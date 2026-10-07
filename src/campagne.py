"""Campagnes d'exécution du recuit (voir notes/meta_heuristique.md, section « Réglage »).

Usage :
    python src/campagne.py reglage [--temps 120] [--jobs 6]
        un facteur à la fois autour de PARAMS, sur INSTANCES_REGLAGE et GRAINES_REGLAGE ;
        résultats dans results/reglage/, synthèse dans results/reglage/synthese.csv
    python src/campagne.py finale [--param nom=valeur ...] [--graines 1 2 3 4 5] [--jobs 6]
        toutes les instances A avec le temps du challenge (ComputationTime) ;
        résultats dans results/, solutions dans solutions/<instance>_metaheuristique_s<g>.txt
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
    args = parser.parse_args()
    if args.campagne == 'reglage':
        reglage(args.temps, args.jobs)
    else:
        params = {}
        for p in args.param:
            nom, _, val = p.partition('=')
            params[nom] = float(val)
        finale(params, args.graines, args.jobs)


if __name__ == '__main__':
    main()
