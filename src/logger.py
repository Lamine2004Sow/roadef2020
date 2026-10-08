"""Enregistrement des résultats pour le rapport (voir notes/rapport.md).

results/instances.csv         caractéristiques des instances
results/results.csv           une ligne par exécution
results/convergence/*.csv     suivi d'une exécution du recuit
"""
import csv
import os
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, 'results')

INSTANCE_COLUMNS = ['instance', 'interventions', 'T', 'ressources', 'exclusions',
                    'scenarios_min', 'scenarios_max', 'alpha', 'quantile', 'temps_limite']
RESULT_COLUMNS = ['date', 'instance', 'methode', 'variante', 'graine',
                  'objectif', 'obj1', 'obj2', 'realisable', 'viol_ressources', 'viol_exclusions',
                  'temps', 'lam', 'a', 'b', 'c', 'T0', 'alpha', 'iterations', 'borne', 'gap']
CONVERGENCE_COLUMNS = ['temps', 'iteration', 'temperature', 'cout_courant', 'meilleur_cout',
                       'taux_acceptation', 'deplacements_acceptes', 'swaps_acceptes']

# Même tolérance que le checker officiel
TOLERANCE = 1e-5


def instance_name(instance_path: str) -> str:
    return os.path.splitext(os.path.basename(instance_path))[0]


def _append(path: str, columns: list, row: dict):
    unknown = set(row) - set(columns)
    if unknown:
        raise ValueError(f'Colonnes inconnues pour {os.path.basename(path)} : {sorted(unknown)}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    if not new:
        # Colonnes ajoutées depuis la création du fichier : réécrire l'en-tête, cases vides
        with open(path, newline='') as f:
            header = next(csv.reader(f), [])
        if header != columns:
            with open(path, newline='') as f:
                old = list(csv.DictReader(f))
            with open(path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows({k: r.get(k, '') for k in columns} for r in old)
    with open(path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if new:
            writer.writeheader()
        writer.writerow({k: row.get(k, '') for k in columns})


def read_csv(path: str) -> list:
    """Lignes d'un CSV en dicts (valeurs numériques converties en float), [] si absent."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            for k, v in row.items():
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    pass
            rows.append(row)
    return rows


def objectifs(ev) -> tuple:
    """(obj1 risque moyen, obj2 excès au quantile) de la solution courante d'une Evaluation."""
    means = np.array([r.mean() for r in ev.risk])
    q = np.array([np.partition(r, k)[k] for r, k in zip(ev.risk, ev.q_idx)])
    return float(means.mean()), float(np.maximum(q - means, 0.0).mean())


def log_instance(instance: dict, instance_path: str, path: str = None):
    """Ajoute la ligne de l'instance dans instances.csv si elle n'y est pas déjà."""
    path = path or os.path.join(RESULTS_DIR, 'instances.csv')
    name = instance_name(instance_path)
    if any(row['instance'] == name for row in read_csv(path)):
        return
    _append(path, INSTANCE_COLUMNS, {
        'instance': name,
        'interventions': len(instance['Interventions']),
        'T': instance['T'],
        'ressources': len(instance['Resources']),
        'exclusions': len(instance['Exclusions']),
        'scenarios_min': min(instance['Scenarios_number']),
        'scenarios_max': max(instance['Scenarios_number']),
        'alpha': instance['Alpha'],
        'quantile': instance['Quantile'],
        'temps_limite': instance.get('ComputationTime', ''),
    })


def log_result(ev, instance_path: str, methode: str, temps: float,
               variante: str = '', graine='', path: str = None, **params):
    """Ajoute une exécution dans results.csv. `params` : lam, a, b, c, T0, alpha, iterations, borne, gap."""
    path = path or os.path.join(RESULTS_DIR, 'results.csv')
    obj1, obj2 = objectifs(ev)
    viol_res = float(ev.res_viol.sum())
    row = {
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'instance': instance_name(instance_path),
        'methode': methode,
        'variante': variante,
        'graine': graine,
        'objectif': ev.objective(),
        'obj1': obj1,
        'obj2': obj2,
        'realisable': int(viol_res <= TOLERANCE and ev.excl_viol == 0),
        'viol_ressources': viol_res,
        'viol_exclusions': ev.excl_viol,
        'temps': temps,
        'lam': ev.lam,
    }
    row.update(params)
    _append(path, RESULT_COLUMNS, row)


class Convergence:
    """Suivi d'une exécution du recuit : une ligne tous les N itérations.

    with Convergence('A_set/A_01.json', 'recuit', graine=0) as conv:
        conv.log(iteration=it, temperature=T, cout_courant=c, meilleur_cout=best,
                 taux_acceptation=acc, deplacements_acceptes=nd, swaps_acceptes=ns)
    """

    def __init__(self, instance_path: str, methode: str, graine='', dossier: str = None):
        dossier = dossier or os.path.join(RESULTS_DIR, 'convergence')
        os.makedirs(dossier, exist_ok=True)
        suffix = f'_s{graine}' if graine != '' else ''
        self.path = os.path.join(dossier, f'{instance_name(instance_path)}_{methode}{suffix}.csv')
        self._file = open(self.path, 'w', newline='')
        self._writer = csv.DictWriter(self._file, fieldnames=CONVERGENCE_COLUMNS)
        self._writer.writeheader()
        self._t0 = time.time()

    def log(self, **values):
        unknown = set(values) - set(CONVERGENCE_COLUMNS)
        if unknown:
            raise ValueError(f'Colonnes inconnues pour la convergence : {sorted(unknown)}')
        values.setdefault('temps', time.time() - self._t0)
        self._writer.writerow(values)

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
