"""Métaheuristique : glouton, puis recuit simulé, puis descente (voir notes/pseudocode_meta_heuristique.md).

Usage : python src/meta_heuristique.py <instance.json> <solution.txt> [--temps S] [--graine G]
                                     [--param nom=valeur ...] [--resultats DOSSIER]
Temps limite par défaut : ComputationTime de l'instance (en minutes).
`--param` remplace une valeur de PARAMS ; `--resultats` écrit results.csv et convergence/ ailleurs
(réglage des paramètres sans mélanger avec les résultats du rapport).
"""
import argparse
import math
import os
import random
import time

from evaluation import Evaluation
from heuristique import glouton
from logger import RESULTS_DIR, Convergence, log_instance, log_result
from reader import read_instance
from writer import write_solution

TOL = 1e-5

PARAMS = {
    'p_swap': 0.3,       # part des swaps parmi les mouvements
    'p_loc': 0.8,        # part des déplacements locaux (±r) parmi les déplacements
    'r': 5,              # rayon des déplacements locaux
    'p0': 0.5,           # taux d'acceptation visé au départ
    'n_calib': 500,      # essais pour calibrer T0
    'ratio_final': 1e-3, # T_final = ratio_final × T0, atteint à la fin du temps limite
    'gamma': 1.01,       # croissance de λ tant que la solution courante est infaisable
}


def cle(ev: Evaluation) -> tuple:
    """Ordre ≺ : moins de violations d'abord, puis meilleur objectif (indépendant de λ)."""
    v = ev.violation()
    return (0.0 if v <= TOL else v, ev.objective())


def appliquer(ev: Evaluation, starts: dict):
    """Ramène ev à la solution `starts` en ne changeant que les dates différentes."""
    changes = {i: s for i, s in starts.items() if ev.start.get(i) != s}
    if changes:
        ev.assign(changes)


class Recuit:

    def __init__(self, ev: Evaluation, rng: random.Random, **params):
        self.ev = ev
        self.rng = rng
        self.p = {**PARAMS, **params}
        self.names = list(ev.start)
        self.smax = {i: min(int(ev.interventions[i]['tmax']), ev.T) for i in self.names}
        self.locaux = [d for d in range(-self.p['r'], self.p['r'] + 1) if d != 0]

    def voisin(self):
        """Algorithme 5 : (changement, type) ou (None, type) si le mouvement tiré est invalide."""
        ev, rng = self.ev, self.rng
        if rng.random() < self.p['p_swap']:
            i, j = rng.sample(self.names, 2)
            if ev.start[i] == ev.start[j]:
                return None, 'swap'
            return ev.swap_changes(i, j), 'swap'
        i = rng.choice(self.names)
        if rng.random() < self.p['p_loc']:
            s = ev.start[i] + rng.choice(self.locaux)
        else:
            s = rng.randint(1, self.smax[i])
        if s == ev.start[i] or not 1 <= s <= self.smax[i]:
            return None, 'deplacement'
        return {i: s}, 'deplacement'

    def calibrer_t0(self) -> tuple:
        """Algorithme 6 : (T0, itérations par seconde mesurées pendant le calibrage).

        Seuls les mouvements qui ne changent pas les violations comptent : sinon la pénalité
        λ·ΔV (ordre 1e5) écrase les variations d'objectif (ordre 1 à 100) et T reste trop haute."""
        ev = self.ev
        t0 = time.time()
        positifs = []
        for _ in range(self.p['n_calib']):
            c, _kind = self.voisin()
            if c:
                v, old = ev.violation(), {i: ev.start[i] for i in c}
                d = ev.assign(c)
                if d > 0 and abs(ev.violation() - v) <= TOL:
                    positifs.append(d)
                ev.assign(old)
        vitesse = self.p['n_calib'] / max(time.time() - t0, 1e-9)
        if not positifs:
            return 1e-6 * max(abs(self.ev.cost()), 1.0), vitesse
        return -(sum(positifs) / len(positifs)) / math.log(self.p['p0']), vitesse

    def run(self, time_limit: float, conv: Convergence = None) -> dict:
        """Algorithme 7 : ramène ev à la meilleure solution rencontrée et retourne les statistiques."""
        ev, rng = self.ev, self.rng
        t_start = time.time()
        T0, vitesse = self.calibrer_t0()
        L = len(self.names)
        # α choisi pour atteindre ratio_final × T0 à la fin du temps restant
        n_paliers = max(1.0, (time_limit - (time.time() - t_start)) * vitesse / L)
        alpha = self.p['ratio_final'] ** (1.0 / n_paliers)

        T = T0
        best_key, best_start = cle(ev), dict(ev.start)
        iterations = 0
        acceptes = {'deplacement': 0, 'swap': 0}
        while time.time() - t_start < time_limit:
            essais = acc = 0
            for _ in range(L):
                c, kind = self.voisin()
                if not c:
                    continue
                essais += 1
                old = {i: ev.start[i] for i in c}
                d = ev.assign(c)
                if d < 0 or rng.random() < math.exp(-d / T):
                    acc += 1
                    acceptes[kind] += 1
                    k = cle(ev)
                    if k < best_key:
                        best_key, best_start = k, dict(ev.start)
                else:
                    ev.assign(old)
            iterations += L
            T *= alpha
            if ev.violation() > TOL:
                ev.set_lambda(ev.lam * self.p['gamma'])
            if conv:
                conv.log(iteration=iterations, temperature=T, cout_courant=ev.cost(),
                         meilleur_cout=best_key[1] + ev.lam * best_key[0],
                         taux_acceptation=acc / max(essais, 1),
                         deplacements_acceptes=acceptes['deplacement'], swaps_acceptes=acceptes['swap'])
        appliquer(ev, best_start)
        return {'T0': T0, 'alpha': alpha, 'iterations': iterations}


def descente(ev: Evaluation, time_limit: float, rng: random.Random) -> Evaluation:
    """Algorithme 8 : déplacements puis swaps améliorants jusqu'au minimum local.
    Un mouvement qui augmente les violations est refusé, même s'il baisse le coût pénalisé."""
    t0 = time.time()

    def essayer(changes: dict) -> bool:
        v = ev.violation()
        old = {i: ev.start[i] for i in changes}
        if ev.delta(changes) >= 0:
            return False
        ev.assign(changes)
        if ev.violation() > v + TOL:
            ev.assign(old)
            return False
        return True

    ameliore = True
    while ameliore and time.time() - t0 < time_limit:
        ameliore = False
        names = list(ev.start)
        rng.shuffle(names)
        for i in names:
            if time.time() - t0 >= time_limit:
                break
            smax = min(int(ev.interventions[i]['tmax']), ev.T)
            d, s = min((ev.delta({i: s}), s) for s in range(1, smax + 1))
            if d < 0 and essayer({i: s}):
                ameliore = True
        spans = {i: ev.span(i) for i in names}
        for a, i in enumerate(names):
            if time.time() - t0 >= time_limit:
                break
            for j in names[a + 1:]:
                (fi, ei), (fj, ej) = spans[i], spans[j]
                if max(fi, fj) >= min(ei, ej) or ev.start[i] == ev.start[j]:
                    continue  # pas de période commune
                changes = ev.swap_changes(i, j)
                if changes and essayer(changes):
                    ameliore = True
                    spans[i], spans[j] = ev.span(i), ev.span(j)
    return ev


def main():
    parser = argparse.ArgumentParser(description='Glouton + recuit simulé + descente')
    parser.add_argument('instance')
    parser.add_argument('solution')
    parser.add_argument('--temps', type=float, help='temps limite total en secondes')
    parser.add_argument('--graine', type=int, default=0)
    parser.add_argument('--param', action='append', default=[], metavar='NOM=VALEUR')
    parser.add_argument('--resultats', default=RESULTS_DIR, help='dossier des CSV')
    args = parser.parse_args()

    params = {}
    for p in args.param:
        nom, _, val = p.partition('=')
        if nom not in PARAMS:
            parser.error(f'paramètre inconnu : {nom} (connus : {", ".join(PARAMS)})')
        params[nom] = type(PARAMS[nom])(float(val)) if isinstance(PARAMS[nom], int) else float(val)
    variante = ' '.join(f'{k}={v:g}' for k, v in params.items())
    csv_resultats = os.path.join(args.resultats, 'results.csv')

    instance = read_instance(args.instance)
    limite = args.temps if args.temps else 60.0 * float(instance.get('ComputationTime', 15))
    rng = random.Random(args.graine)
    t0 = time.time()

    ev = glouton(instance, temps_reparation=0.2 * limite)
    t_glouton = time.time() - t0
    print(f'Glouton  : objectif = {ev.objective():.4f} | violations = {ev.violation():.4f} | {t_glouton:.1f} s')

    # Un fichier de convergence par variante : les essais du réglage ne s'écrasent pas
    nom_conv = 'recuit' + ('_' + variante.replace(' ', '_') if variante else '')
    with Convergence(args.instance, nom_conv, args.graine,
                     dossier=os.path.join(args.resultats, 'convergence')) as conv:
        stats = Recuit(ev, rng, **params).run(0.9 * limite - (time.time() - t0), conv)
    t_recuit = time.time() - t0
    log_instance(instance, args.instance)
    log_result(ev, args.instance, 'recuit', t_recuit, variante=variante, graine=args.graine, path=csv_resultats,
               T0=stats['T0'], alpha=stats['alpha'], iterations=stats['iterations'])
    print(f'Recuit   : objectif = {ev.objective():.4f} | violations = {ev.violation():.4f} '
          f'| {stats["iterations"]} itérations | {t_recuit:.1f} s')

    descente(ev, limite - (time.time() - t0), rng)
    t_total = time.time() - t0
    log_result(ev, args.instance, 'recuit+descente', t_total, variante=variante, graine=args.graine,
               path=csv_resultats,
               T0=stats['T0'], alpha=stats['alpha'], iterations=stats['iterations'])
    print(f'Descente : objectif = {ev.objective():.4f} | violations = {ev.violation():.4f} | {t_total:.1f} s')
    write_solution(args.solution, ev.start)


if __name__ == '__main__':
    main()
