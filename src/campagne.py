"""Campagnes d'exécution du recuit et de la PLNE (voir notes/meta_heuristique.md et notes/plne.md).

Usage :
    python src/campagne.py reglage [--temps 120] [--jobs 6]
        un facteur à la fois autour de PARAMS, sur INSTANCES_REGLAGE et GRAINES_REGLAGE ;
        résultats dans results/reglage/, synthèse dans results/reglage/synthese.csv
    python src/campagne.py finale [--param nom=valeur ...] [--graines 1 2 3 4 5] [--jobs 6]
        toutes les instances A avec le temps du challenge (ComputationTime) ;
        résultats dans results/, solutions dans solutions/<instance>_metaheuristique_s<g>.txt
    python src/campagne.py plne [--temps S] [--jobs 1] [--threads 0] [--memoire 8] [--coupes] [--instances A_07 ...]
        PLNE sur les instances A (temps du challenge par défaut), une à la fois par défaut,
        en partant de la meilleure solution réalisable du recuit (MIP start) ;
        solutions dans solutions/<instance>_plne.txt, logs dans results/logs/<instance>_plne.log ;
        --coupes : coupes de quantile (solutions et logs suffixés _coupes)
"""
import argparse
import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from logger import RESULTS_DIR, ROOT, read_csv
from meta_heuristique import PARAMS

PYTHON = sys.executable
# Tailles et écarts glouton / meilleur connu variés ; graines distinctes de la campagne finale
INSTANCES_REGLAGE = ['A_06', 'A_09', 'A_13']
GRAINES_REGLAGE = [100, 101]
GRILLE = {
    'p_swap': [0.0, 0.15, 0.3, 0.5],
    'p_loc': [0.5, 0.8, 0.95],
    'r': [2, 5, 10],
    'p0': [0.2, 0.5, 0.8],
    'ratio_final': [1e-2, 1e-3, 1e-4],
}
# Les plus grosses d'abord : elles finissent avec les autres plutôt qu'en dernier, seules
ORDRE_FINALE = ['A_05', 'A_04', 'A_02', 'A_06', 'A_01', 'A_13', 'A_03',
                'A_10', 'A_14', 'A_15', 'A_11', 'A_12', 'A_07', 'A_08', 'A_09']


def instance_path(nom: str) -> str:
    return os.path.join(ROOT, 'A_set', f'{nom}.json')


def lancer(cmd: list, log: str) -> int:
    with open(log, 'w') as f:
        return subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)


def executer(taches: list, jobs: int):
    """taches : [(cmd, log)] ; affiche l'avancement."""
    total = len(taches)

    def une(k_tache):
        k, (cmd, log) = k_tache
        code = lancer(cmd, log)
        print(f'[{k + 1}/{total}] {"ok" if code == 0 else f"ÉCHEC ({code})"}  {os.path.basename(log)}',
              flush=True)
        return code

    with ThreadPoolExecutor(jobs) as pool:
        codes = list(pool.map(une, enumerate(taches)))
    if any(codes):
        print(f'{sum(c != 0 for c in codes)} exécution(s) en échec, voir les .log')


def args_param(params: dict) -> list:
    return [x for k, v in params.items() for x in ('--param', f'{k}={v:g}')]


# ------------------------------------------------------------------- réglage

def configurations() -> list:
    """Défaut, puis chaque facteur à une autre valeur (les autres au défaut)."""
    confs = [{}]
    for nom, valeurs in GRILLE.items():
        confs += [{nom: v} for v in valeurs if v != PARAMS[nom]]
    return confs


def reglage(temps: float, jobs: int):
    dossier = os.path.join(RESULTS_DIR, 'reglage')
    os.makedirs(os.path.join(dossier, 'logs'), exist_ok=True)
    taches = []
    for conf in configurations():
        slug = '_'.join(f'{k}={v:g}' for k, v in conf.items()) or 'defaut'
        for inst in INSTANCES_REGLAGE:
            for g in GRAINES_REGLAGE:
                sol = os.path.join(dossier, 'solutions', f'{inst}_{slug}_s{g}.txt')
                os.makedirs(os.path.dirname(sol), exist_ok=True)
                cmd = [PYTHON, 'src/meta_heuristique.py', instance_path(inst), sol,
                       '--temps', str(temps), '--graine', str(g), '--resultats', dossier] + args_param(conf)
                taches.append((cmd, os.path.join(dossier, 'logs', f'{inst}_{slug}_s{g}.log')))
    print(f'{len(taches)} exécutions de {temps:g} s sur {jobs} cœurs')
    executer(taches, jobs)
    synthese(dossier)


def synthese(dossier: str):
    """Écart moyen (%) au meilleur objectif trouvé pendant le réglage, par variante."""
    rows = [r for r in read_csv(os.path.join(dossier, 'results.csv')) if r['methode'] == 'recuit+descente']
    best = {}
    for r in rows:
        if r['realisable'] == 1:
            best[r['instance']] = min(best.get(r['instance'], float('inf')), r['objectif'])
    par_var = {}
    for r in rows:
        v = r['variante'] if isinstance(r['variante'], str) and r['variante'] else 'defaut'
        e = 100 * (r['objectif'] - best[r['instance']]) / best[r['instance']] if r['realisable'] == 1 else float('inf')
        par_var.setdefault(v, {}).setdefault(r['instance'], []).append(e)
    lignes = []
    for v, d in par_var.items():
        par_inst = {i: sum(e) / len(e) for i, e in d.items()}
        lignes.append({'variante': v, 'ecart_moyen': sum(par_inst.values()) / len(par_inst),
                       **{f'ecart_{i}': par_inst.get(i, '') for i in INSTANCES_REGLAGE}})
    lignes.sort(key=lambda x: x['ecart_moyen'])
    with open(os.path.join(dossier, 'synthese.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f'\n{"variante":<22}{"moyenne":>9}' + ''.join(f'{i:>9}' for i in INSTANCES_REGLAGE))
    for l in lignes:
        print(f'{l["variante"]:<22}{l["ecart_moyen"]:>8.3f}%'
              + ''.join(f'{l[f"ecart_{i}"]:>8.3f}%' for i in INSTANCES_REGLAGE))


# ---------------------------------------------------------------------- plne

# Plus petits modèles d'abord : leurs résultats sont acquis même si une grosse instance échoue
ORDRE_PLNE = ['A_07', 'A_09', 'A_12', 'A_10', 'A_08', 'A_11', 'A_03', 'A_14', 'A_15',
              'A_01', 'A_13', 'A_06', 'A_02', 'A_04', 'A_05']


def meilleur_recuit(inst: str):
    """Solution réalisable de la campagne finale avec le meilleur objectif, ou None."""
    rows = [r for r in read_csv(os.path.join(RESULTS_DIR, 'results.csv'))
            if r['instance'] == inst and r['methode'] == 'recuit+descente' and r['realisable'] == 1
            and r['graine'] != '' and not r['variante']]
    for r in sorted(rows, key=lambda r: r['objectif']):
        sol = os.path.join(ROOT, 'solutions', f'{inst}_metaheuristique_s{int(r["graine"])}.txt')
        if os.path.exists(sol):
            return sol
    return None


def plne(instances: list, temps: float, jobs: int, threads: int, memoire: float, avec_coupes: bool = False):
    logs = os.path.join(RESULTS_DIR, 'logs')
    os.makedirs(logs, exist_ok=True)
    taches = []
    for inst in instances:
        nom = f'{inst}_plne' + ('_coupes' if avec_coupes else '')
        sol = os.path.join(ROOT, 'solutions', f'{nom}.txt')
        cmd = [PYTHON, 'src/Plne.py', instance_path(inst), sol, '--threads', str(threads)]
        if avec_coupes:
            cmd += ['--coupes']
        if temps:
            cmd += ['--temps', str(temps)]
        if memoire:
            cmd += ['--memoire', str(memoire)]
        depart = meilleur_recuit(inst)
        if depart:
            cmd += ['--depart', depart]
        print(f'{inst} : départ {os.path.basename(depart) if depart else "aucun"}')
        cmd = ['sh', '-c', ' '.join(f"'{a}'" for a in cmd)
               + f" && '{PYTHON}' RTE_ChallengeROADEF2020_checker.py '{instance_path(inst)}' '{sol}'"]
        taches.append((cmd, os.path.join(logs, f'{nom}.log')))
    print(f'{len(taches)} PLNE, {jobs} à la fois, {threads or "tous les"} cœurs chacune')
    executer(taches, jobs)


# -------------------------------------------------------------------- finale

def finale(params: dict, graines: list, jobs: int):
    os.makedirs(os.path.join(ROOT, 'solutions'), exist_ok=True)
    logs = os.path.join(RESULTS_DIR, 'logs')
    os.makedirs(logs, exist_ok=True)
    taches = []
    for g in graines:
        for inst in ORDRE_FINALE:
            sol = os.path.join(ROOT, 'solutions', f'{inst}_metaheuristique_s{g}.txt')
            # Exécution puis vérification par le checker officiel, dans le même log
            cmd = ['sh', '-c', ' '.join(
                [PYTHON, 'src/meta_heuristique.py', instance_path(inst), sol, '--graine', str(g)]
                + [f"'{a}'" for a in args_param(params)]
                + ['&&', PYTHON, 'RTE_ChallengeROADEF2020_checker.py', instance_path(inst), sol])]
            taches.append((cmd, os.path.join(logs, f'{inst}_metaheuristique_s{g}.log')))
    print(f'{len(taches)} exécutions au temps du challenge sur {jobs} cœurs')
    executer(taches, jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='campagne', required=True)
    r = sub.add_parser('reglage')
    r.add_argument('--temps', type=float, default=120)
    r.add_argument('--jobs', type=int, default=6)
    f = sub.add_parser('finale')
    f.add_argument('--param', action='append', default=[], metavar='NOM=VALEUR')
    f.add_argument('--graines', type=int, nargs='+', default=[1, 2, 3, 4, 5])
    f.add_argument('--jobs', type=int, default=6)
    p = sub.add_parser('plne')
    p.add_argument('--temps', type=float, help='secondes (défaut : ComputationTime)')
    p.add_argument('--jobs', type=int, default=1, help='PLNE simultanées')
    p.add_argument('--threads', type=int, default=0, help='cœurs par PLNE (0 : tous)')
    p.add_argument('--memoire', type=float, default=8, help='mémoire max de Gurobi en Go')
    p.add_argument('--coupes', action='store_true', help='coupes de quantile (voir notes/plne.md)')
    p.add_argument('--instances', nargs='+', default=ORDRE_PLNE)
    args = parser.parse_args()
    if args.campagne == 'reglage':
        reglage(args.temps, args.jobs)
    elif args.campagne == 'plne':
        plne(args.instances, args.temps, args.jobs, args.threads, args.memoire, args.coupes)
    else:
        params = {}
        for p in args.param:
            nom, _, val = p.partition('=')
            params[nom] = float(val)
        finale(params, args.graines, args.jobs)


if __name__ == '__main__':
    main()
