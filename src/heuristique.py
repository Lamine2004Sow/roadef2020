"""Heuristique gloutonne. Usage : python src/heuristique.py <instance.json> <solution.txt>

Interventions triées de la plus difficile à la plus facile, puis placées une à une
à la date qui augmente le moins le coût pénalisé (voir notes/pseudocode_heuristique.md).
"""
import random
import sys
import time

import numpy as np

from evaluation import Evaluation
from indicateurs import compute_indicators, difficulty_scores
from logger import log_instance, log_result
from reader import read_instance, start_candidates
from writer import write_solution

# λ = BETA × risque moyen des interventions : réduire une violation passe avant réduire le risque
BETA = 10.0


def lambda_defaut(indicators: dict) -> float:
    return BETA * float(np.mean([x['R_moy'] for x in indicators.values()]))


def meilleure_date(ev: Evaluation, i: str, k: int = 1, rng: random.Random = None) -> int:
    """Algorithme 1 : meilleure date de début de i, ou tirage parmi les k meilleures (GRASP)."""
    candidates = [(ev.delta({i: s}), s) for s in start_candidates(ev.interventions[i], ev.T)]
    if k == 1:
        return min(candidates)[1]
    candidates.sort()
    return (rng or random).choice(candidates[:k])[1]


def glouton(instance: dict, k: int = 1, lam: float = None, seed: int = None,
            a: float = 1.0, b: float = 1.0, c: float = 0.5) -> Evaluation:
    """Algorithme 2 : construction gloutonne, retourne l'Evaluation de la solution complète."""
    indicators = compute_indicators(instance)
    scores = difficulty_scores(indicators, a, b, c)
    ordre = sorted(scores, key=scores.get, reverse=True)
    ev = Evaluation(instance, lam if lam is not None else lambda_defaut(indicators))
    rng = random.Random(seed)
    for i in ordre:
        ev.assign({i: meilleure_date(ev, i, k, rng)})
    return ev


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage : python src/heuristique.py <instance.json> <solution.txt>')
    instance = read_instance(sys.argv[1])
    a, b, c = 1.0, 1.0, 0.5
    t0 = time.time()
    ev = glouton(instance, a=a, b=b, c=c)
    elapsed = time.time() - t0
    write_solution(sys.argv[2], ev.start)
    log_instance(instance, sys.argv[1])
    log_result(ev, sys.argv[1], 'glouton', elapsed, variante=f'a={a:g} b={b:g} c={c:g}', a=a, b=b, c=c)
    print(f'Glouton : objectif = {ev.objective():.4f} | violations = {ev.violation():.4f} '
          f'| λ = {ev.lam:.4g} | temps = {elapsed:.2f} s')


if __name__ == '__main__':
    main()
