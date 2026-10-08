"""PLNE complète avec Gurobi (voir notes/plne.md).

Usage : python src/Plne.py <instance.json> <solution.txt> [--temps S] [--depart solution.txt] [--threads N]
                                                  [--memoire GO]
Temps limite par défaut : ComputationTime de l'instance (en minutes).
`--depart` fournit une solution de départ (par exemple la meilleure du recuit) comme MIP start.

Modèle (indices de périodes et de dates de début à partir de 1, comme l'instance) :
    x[i,s] ∈ {0,1}   l'intervention i commence en s           Σ_s x[i,s] = 1
    r[t,ω] = Σ_{i,s} risk_i[t][s][ω] · x[i,s]                 risque du scénario ω en t
    m[t]   = (1/S_t) Σ_ω r[t,ω]                               risque moyen
    Q[t]   ≥ quantile τ de {r[t,ω]} :  r[t,ω] ≤ Q[t] + M[t,ω] · y[t,ω],  Σ_ω y[t,ω] ≤ S_t − k_t
           (k_t = ⌈τ S_t⌉ : au moins k_t scénarios sous Q[t], comme le checker)
    E[t]   ≥ Q[t] − m[t],  E[t] ≥ 0                           excès
    min (1/T) Σ_t [ α m[t] + (1 − α) E[t] ]
    ressources : min_c[t] ≤ Σ_{i,s} workload_i[c][t][s] · x[i,s] ≤ max_c[t]
    exclusions : pour (i, j, saison) et t dans la saison, au plus une des deux en cours en t
"""
import argparse
import math
import sys
import time
from collections import defaultdict

try:
    import gurobipy as gp
except ImportError:
    gp = None

from evaluation import Evaluation
from logger import log_instance, log_result
from reader import read_instance, read_solution, start_candidates, duration
from writer import write_solution

# Au-delà de cette taille, la licence gratuite fournie avec `pip install gurobipy` refuse le modèle
RESTRICTED_LIMIT = 2000


def gurobi_env():
    """Retourne un environnement Gurobi, ou arrête le programme avec un message clair
    si gurobipy est absent, sans licence, ou avec la licence restreinte de pip."""
    if gp is None:
        sys.exit("PLNE indisponible : gurobipy n'est pas installé (lancer `make install`).")
    try:
        env = gp.Env(empty=True)
        env.setParam('OutputFlag', 0)
        env.start()
        # Test de taille : échoue avec l'erreur SIZE_LIMIT_EXCEEDED si la licence est restreinte
        with gp.Model(env=env) as m:
            m.addVars(RESTRICTED_LIMIT + 1)
            m.optimize()
    except gp.GurobiError as e:
        if e.errno == gp.GRB.Error.SIZE_LIMIT_EXCEEDED:
            sys.exit('PLNE indisponible : licence Gurobi restreinte (limitée à 2000 variables). '
                     'Une licence complète (académique gratuite) est requise.')
        sys.exit(f'PLNE indisponible : licence Gurobi introuvable ou invalide '
                 f'(vérifier GRB_LICENSE_FILE). Détail : {e}')
    return env


def construire(instance: dict, env) -> tuple:
    """Modèle complet ; retourne (modèle, x) avec x[(i, s)] la variable de début."""
    GRB = gp.GRB
    T = instance['T']
    alpha, tau = instance['Alpha'], instance['Quantile']
    S = instance['Scenarios_number']
    interventions = instance['Interventions']
    m = gp.Model('roadef2020', env=env)

    x = {}
    for i, interv in interventions.items():
        for s in start_candidates(interv, T):
            x[i, s] = m.addVar(vtype=GRB.BINARY, name=f'x[{i},{s}]')
    for i, interv in interventions.items():
        m.addConstr(gp.quicksum(x[i, s] for s in start_candidates(interv, T)) == 1, name=f'debut[{i}]')

    # Termes par période : risque par scénario, risque moyen, charges, interventions en cours
    risque = [defaultdict(lambda: ([], [])) for _ in range(T)]   # risque[t][ω] = (coefs, vars)
    moyenne = [([], []) for _ in range(T)]
    charge = defaultdict(lambda: ([], []))                         # charge[c, t] = (coefs, vars)
    en_cours = defaultdict(list)                                   # en_cours[i, t] = [x[i, s]]
    r_max = [defaultdict(float) for _ in range(T)]                 # bornes pour les big-M
    r_min = [defaultdict(float) for _ in range(T)]
    for i, interv in interventions.items():
        # Contribution extrême de i au scénario ω en t, sur toutes ses dates (0 si i n'y est pas)
        hi, lo = defaultdict(float), defaultdict(float)
        for s in start_candidates(interv, T):
            v = x[i, s]
            actives = range(s, min(s + duration(interv, s), T + 1))
            for t in actives:
                en_cours[i, t].append(v)
                vals = interv['risk'][str(t)][str(s)]
                co, va = risque[t - 1], moyenne[t - 1]
                for w, r in enumerate(vals):
                    if r:
                        co[w][0].append(r)
                        co[w][1].append(v)
                        hi[t, w] = max(hi[t, w], r)
                        lo[t, w] = min(lo[t, w], r)
                mu = sum(vals) / S[t - 1]
                if mu:
                    va[0].append(mu)
                    va[1].append(v)
            # Comme le checker : charge comptée seulement pendant que i est en cours
            for c, wl in interv['workload'].items():
                for t in actives:
                    val = wl.get(str(t), {}).get(str(s))
                    if val:
                        charge[c, t][0].append(val)
                        charge[c, t][1].append(v)
        for (t, w), val in hi.items():
            r_max[t - 1][w] += val
        for (t, w), val in lo.items():
            r_min[t - 1][w] += val

    # Ressources
    for c, res in instance['Resources'].items():
        for t in range(1, T + 1):
            co, va = charge.get((c, t), ([], []))
            expr = gp.LinExpr(co, va)
            lo_c, hi_c = res['min'][t - 1], res['max'][t - 1]
            if va:
                m.addConstr(expr <= hi_c, name=f'rmax[{c},{t}]')
            if lo_c > 0:
                m.addConstr(expr >= lo_c, name=f'rmin[{c},{t}]')

    # Exclusions
    saisons = {k: {int(p) for p in v} for k, v in instance['Seasons'].items()}
    for nom, (i1, i2, saison) in instance['Exclusions'].items():
        for t in saisons.get(saison, ()):
            a, b = en_cours.get((i1, t)), en_cours.get((i2, t))
            if a and b:
                m.addConstr(gp.quicksum(a) + gp.quicksum(b) <= 1, name=f'excl[{nom},{t}]')

    # Objectif : risque moyen et excès du quantile
    obj = gp.LinExpr()
    for t in range(T):
        mu = gp.LinExpr(*moyenne[t])
        obj += alpha * mu
        k = math.ceil(S[t] * tau)
        if alpha == 1 or S[t] == 1:
            continue  # pas d'excès : terme nul ou quantile = moyenne
        # Q[t] ≥ min_ω r[t,ω] ≥ Σ_i (contribution minimale de i) : borne valide, donne les big-M
        q_lb = min(0.0, min(r_min[t].get(w, 0.0) for w in range(S[t])))
        q = m.addVar(lb=q_lb, name=f'Q[{t + 1}]')
        e = m.addVar(lb=0.0, name=f'E[{t + 1}]')
        m.addConstr(e >= q - mu, name=f'exces[{t + 1}]')
        if k < S[t]:
            y = m.addVars(S[t], vtype=GRB.BINARY, name=f'y[{t + 1}]')
            m.addConstr(y.sum() <= S[t] - k, name=f'quantile[{t + 1}]')
            for w in range(S[t]):
                big_m = r_max[t].get(w, 0.0) - q_lb
                m.addConstr(gp.LinExpr(*risque[t][w]) <= q + big_m * y[w], name=f'q[{t + 1},{w}]')
        else:
            for w in range(S[t]):  # τ = 1 : Q[t] est le maximum
                m.addConstr(gp.LinExpr(*risque[t][w]) <= q, name=f'q[{t + 1},{w}]')
        obj += (1 - alpha) * e
    m.setObjective(obj * (1.0 / T), GRB.MINIMIZE)
    return m, x


def main():
    parser = argparse.ArgumentParser(description='PLNE complète (Gurobi)')
    parser.add_argument('instance')
    parser.add_argument('solution')
    parser.add_argument('--temps', type=float, help='temps limite de résolution en secondes')
    parser.add_argument('--depart', help='solution de départ (MIP start)')
    parser.add_argument('--threads', type=int, default=0, help='0 : tous les cœurs')
    parser.add_argument('--memoire', type=float, help='mémoire max de Gurobi en Go (arrêt propre au-delà)')
    args = parser.parse_args()

    env = gurobi_env()
    instance = read_instance(args.instance)
    limite = args.temps if args.temps else 60.0 * float(instance.get('ComputationTime', 15))
    t0 = time.time()
    m, x = construire(instance, env)
    m.update()
    t_construction = time.time() - t0
    print(f'Modèle   : {m.NumVars} variables ({m.NumBinVars} binaires), {m.NumConstrs} contraintes, '
          f'{m.NumNZs} non-zéros | {t_construction:.1f} s')

    if args.depart:
        for (i, s), v in x.items():
            v.Start = 0.0
        for i, s in read_solution(args.depart).items():
            if (i, s) in x:
                x[i, s].Start = 1.0
    m.Params.OutputFlag = 1
    m.Params.TimeLimit = max(1.0, limite - t_construction)
    m.Params.Threads = args.threads
    m.Params.MIPGap = 0.0  # optimum exact quand il est atteint (défaut Gurobi : 0,01 %)
    if args.memoire:
        m.Params.MemLimit = args.memoire  # statut MEM_LIMIT, garde la meilleure solution trouvée
    m.optimize()
    temps = time.time() - t0

    if m.SolCount == 0:
        sys.exit(f'PLNE : aucune solution trouvée en {temps:.0f} s (statut {m.Status}).')
    starts = {i: s for (i, s), v in x.items() if v.X > 0.5}
    write_solution(args.solution, starts)

    ev = Evaluation(instance)
    ev.assign(starts)
    borne = m.ObjBound
    gap = m.MIPGap
    log_instance(instance, args.instance)
    log_result(ev, args.instance, 'plne', temps, borne=borne, gap=gap)
    statut = 'optimal' if m.Status == gp.GRB.OPTIMAL else f'statut {m.Status}'
    print(f'PLNE     : objectif = {ev.objective():.4f} | violations = {ev.violation():.4f} '
          f'| borne = {borne:.4f} | gap = {100 * gap:.3f} % | {statut} | {temps:.1f} s')


if __name__ == '__main__':
    main()
