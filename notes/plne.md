# PLNE (Gurobi)

Fichier : `src/Plne.py` — `make plne INSTANCE=... [TEMPS=900] [DEPART=solution.txt]`
(temps par défaut : `ComputationTime` de l'instance ; `DEPART` : solution de départ, par exemple la
meilleure du recuit, donnée à Gurobi comme MIP start).

## Dépendance à Gurobi

- Seule méthode du projet qui utilise Gurobi ; glouton et recuit n'en dépendent pas.
- **Pas de solveur alternatif** (PuLP + HiGHS/CBC écarté) : sans Gurobi, les solveurs libres
  ne résoudraient que les petites instances A, pour beaucoup de code en plus.
- `gurobi_env()` arrête proprement le programme avec un message clair si :
  - `gurobipy` n'est pas installé ;
  - la licence est introuvable ou invalide (`GRB_LICENSE_FILE`) ;
  - la licence est la licence restreinte de pip (> 2000 variables refusées), détectée par un
    modèle test de 2001 variables (erreur `SIZE_LIMIT_EXCEEDED`).
- Licence actuelle : académique, valable jusqu'au 2027-09-02.

## Modèle complet (`construire`)

Notations : `I` interventions, `T` périodes, `S_t` scénarios en `t`, `τ` quantile, `α` poids.
Une intervention `i` commencée en `s` est en cours sur `s .. s + Δ_i(s) − 1` (tronqué à `T`).

| Élément | Formulation |
|---|---|
| Variables de début | `x[i,s] ∈ {0,1}`, `s = 1 .. min(tmax_i, T)`, `Σ_s x[i,s] = 1` |
| Risque du scénario ω | `r[t,ω] = Σ_{i,s} risk_i[t][s][ω] · x[i,s]` (expression linéaire) |
| Risque moyen | `m[t] = (1/S_t) Σ_ω r[t,ω]` |
| Quantile | `Q[t]` continue, `y[t,ω] ∈ {0,1}` : `r[t,ω] ≤ Q[t] + M[t,ω] · y[t,ω]`, `Σ_ω y[t,ω] ≤ S_t − k_t` |
| Excès | `E[t] ≥ Q[t] − m[t]`, `E[t] ≥ 0` |
| Objectif | `min (1/T) Σ_t [ α m[t] + (1 − α) E[t] ]` |
| Ressources | `min_c[t] ≤ Σ_{i,s} workload_i[c][t][s] · x[i,s] ≤ max_c[t]` (charge comptée pendant que `i` est en cours, comme le checker) |
| Exclusions | pour `(i, j, saison)` et `t` dans la saison : `Σ_{s : i en cours en t} x[i,s] + Σ_{s : j en cours en t} x[j,s] ≤ 1` |

**Quantile.** Le checker prend la `k_t`-ième plus petite valeur, `k_t = ⌈τ S_t⌉`. Les contraintes
imposent qu'au moins `k_t` scénarios soient sous `Q[t]`, donc `Q[t]` ≥ quantile ; comme l'objectif
pénalise `E[t]`, l'optimum ramène `Q[t]` au quantile exact. Seul le terme d'excès est non convexe :
c'est lui qui demande une binaire `y[t,ω]` par scénario.

**Big-M.** `M[t,ω] = Σ_i max_s risk_i[t][s][ω] − LB(Q[t])`, avec `LB(Q[t]) = min(0, min_ω Σ_i min_s risk_i[t][s][ω])`
(contributions extrêmes de chaque intervention, 0 si elle n'est pas en cours). Plus `M` est serré,
meilleure est la borne inférieure.

**Cas simplifiés.** `S_t = 1` (quantile = moyenne) ou `α = 1` : pas de `Q`, `E`, `y`. `k_t = S_t` : `Q[t] ≥ r[t,ω]` sans binaire.

`MIPGap = 0` : un statut « optimal » est un optimum exact (tolérance Gurobi par défaut : 0,01 %).
Chaque exécution ajoute une ligne `plne` à `results.csv`, avec les colonnes `borne` (meilleure borne
inférieure) et `gap`.

## Premiers résultats (tests, 60 à 120 s, MIP start : recuit graine 1)

Toutes les solutions ont été vérifiées par le checker officiel (objectif identique, aucune violation).

| Instance | Variables (binaires) | Non-zéros | Statut | Objectif | Borne | Gap | Temps |
|---|---|---|---|---|---|---|---|
| A_07 | 727 (693) | 8 844 | optimal | 2272,7823 | 2272,7823 | 0 | 0,1 s |
| A_09 | 422 (388) | 5 697 | optimal | 1507,2848 | 1507,2848 | 0 | 0,1 s |
| A_10 | 5 979 (5 873) | 94 678 | optimal | 2994,8487 | 2994,8487 | 0 | 3,0 s |
| A_12 | 3 236 (3 130) | 36 620 | optimal | 789,6349 | 789,6349 | 0 | 0,9 s |
| A_08 | 11 312 (11 278) | 261 399 | limite 120 s | 744,2932 | 690,9004 | 7,17 % | 120 s |
| A_11 | 36 831 (36 725) | 2 183 056 | limite 120 s | 495,2714 | 457,4176 | 7,64 % | 120 s |

- A_07, A_09, A_10, A_12 (5 ou 6 scénarios) : **optimum prouvé**, égal à la meilleure valeur du
  challenge → la meilleure des 5 graines du recuit atteint l'optimum sur ces quatre instances
  (A_10, graine 1 : 2995,17, amélioré par la PLNE jusqu'à l'optimum 2994,85).
- A_08, A_11 (≈ 600 scénarios, τ = 0,95) : la relaxation du quantile est faible (big-M), la borne
  progresse lentement ; la solution reste celle du recuit (pas d'amélioration en 120 s).
- Comparaison : Gouvine (voir `notes/bibliographie.md`) rapporte avec son modèle « Full »
  (indicator constraints, CPLEX, 1 h) des gaps de 6,31 % sur A_08 et 8,72 % sur A_11, du même ordre
  que les nôtres en 120 s ; sa génération de contraintes prouve l'optimum de A_08.

## À faire

- [x] Modèle : variables de date de début, ressources, exclusions, linéarisation du quantile.
- [ ] Campagne au temps du challenge sur les 15 instances A : `python src/campagne.py plne`
      (une PLNE à la fois sur tous les cœurs, ≈ 4 h ; plus petits modèles d'abord ; départ : meilleure
      graine du recuit ; `MemLimit` 12 Go car non-zéros ≈ Σ_{i,s} Δ·S_t, à surveiller sur A_02, A_04, A_05).
- [ ] Piste d'amélioration de la borne : génération de contraintes sur les scénarios (Gouvine).
