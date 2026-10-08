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

## Résultats au temps du challenge (`python src/campagne.py plne`)

15 instances A, `ComputationTime` = 15 min (construction du modèle comprise), une PLNE à la fois sur
les 8 cœurs, `MemLimit` 8 Go (15 Go de RAM sur la machine), MIP start : meilleure graine du recuit.
**15/15 solutions réalisables** selon le checker officiel. Tableau complet avec glouton et recuit :
`results/tableau.md` (`make tableau`).

| Instance | Scénarios (max) | Statut | PLNE | Borne | Gap certifié | Temps |
|---|---|---|---|---|---|---|
| A_01 | 1 | optimal | 1767,82 | 1767,82 | 0 | 2,6 s |
| A_03 | 1 | optimal | 848,18 | 848,18 | 0 | 0,5 s |
| A_04 | 1 | optimal | 2085,88 | 2085,88 | 0 | 112 s |
| A_06 | 1 | optimal | 590,62 | 590,62 | 0 | 4,1 s |
| A_07 | 6 | optimal | 2272,78 | 2272,78 | 0 | 0,1 s |
| A_09 | 6 | optimal | 1507,28 | 1507,28 | 0 | 0,1 s |
| A_10 | 6 | optimal | 2994,85 | 2994,85 | 0 | 2,6 s |
| A_12 | 6 | optimal | 789,63 | 789,63 | 0 | 0,8 s |
| A_13 | 12 | limite | 1998,84 | 1998,36 | 0,02 % | 900 s |
| A_05 | 120 | limite | 635,37 | 593,49 | 6,59 % | 900 s |
| A_02 | 120 | limite | 4672,13 | 2058,39 | 55,94 % | 900 s |
| A_08 | 693 | limite | 744,29 | 700,11 | 5,94 % | 900 s |
| A_11 | 693 | limite | 495,27 | 460,59 | 7,00 % | 900 s |
| A_14 | 174 | limite | 2312,36 | 2080,06 | 10,05 % | 900 s |
| A_15 | 347 | limite | 2314,92 | 2071,06 | 10,53 % | 900 s |

- **Optimum prouvé sur 8 instances**, toutes égales à la meilleure valeur du challenge : les 4 à un
  seul scénario (pas de quantile, A_04 compris malgré 252 114 binaires) et les 4 à 6 scénarios.
  Sur A_01, A_04 et A_06, la PLNE améliore le meilleur recuit jusqu'à l'optimum (A_06 : 594,69 → 590,62).
- Dès 12 scénarios, le temps limite est atteint : la PLNE n'améliore le départ du recuit que de 0,4 au plus
  (A_13 : 1999,00 → 1998,84 ; A_14 : 2312,69 → 2312,36 ; inchangé sur A_02, A_05, A_08). Son intérêt y est la **borne** : elle certifie
  que le meilleur recuit est à moins de 6 à 11 % de l'optimum (A_08, A_11, A_14, A_15, A_05).
- A_02 (120 scénarios, 4,1 M de non-zéros) : borne très faible (gap 56 %), le big-M du quantile ne
  serre presque rien ; A_05, même nombre de scénarios, reste à 6,6 %.
- Mémoire : aucune PLNE n'a atteint les 8 Go.

## Coupes de quantile (`--coupes`)

**Pourquoi la borne de A_02 est faible.** L'excès pèse plus que le risque moyen (obj2 = 4943 contre
obj1 = 4401) mais, en relaxation, les `y[t,ω]` fractionnaires annulent presque les big-M : Q[t] n'est
plus borné et la borne (2058) ne compte guère que la moyenne.

**Essai abandonné : génération de contraintes sur les scénarios (CGen de Gouvine).** Modèle restreint
à W_t ⊂ scénarios (au moins |W_t| − (S_t − k_t) sous Q[t] : relaxation valide), on ajoute les
scénarios au-dessus de Q[t] et on recommence. Sur A_02, 9 scénarios par période : 272 s pour résoudre
le modèle restreint à 1 %, borne 1624 ; 13 scénarios : 2054. Le goulot n'est pas le nombre de binaires
mais le big-M, et les petits W_t donnent un rang de quantile trop bas.

**Coupe retenue.** Au plus `S_t − k_t` scénarios dépassent Q[t] : tout ensemble W de `S_t − k_t + 1`
scénarios en contient un sous Q[t], et comme chaque intervention n'a qu'une date de début :

    Q[t] ≥ min_{ω∈W} r[t,ω] ≥ Σ_{i,s} ( min_{ω∈W} risk_i[t][s][ω] ) · x[i,s]

Coupe linéaire, valide pour toute solution entière, sans binaire. Elle est forte quand les scénarios
sont corrélés : sur la meilleure solution de A_02, avec W = ses 7 scénarios les plus hauts, elle
retrouve 96 % de l'excès (4763 sur 4943).

**Mise en œuvre** (`coupes`, `separer`, `callback_coupes` dans `src/Plne.py`) :
1. relaxation linéaire sans `y` ni big-M (Q[t] borné par les seules coupes), coupes initiales tirées
   de la solution de départ ;
2. séparation : en chaque t, W = les `S_t − k_t + 1` scénarios les plus hauts de la solution relâchée ;
   on ajoute la coupe si elle est violée, jusqu'à ce qu'aucune ne le soit (20 % du temps au plus) ;
3. les coupes sont ajoutées à la PLNE complète (qui reste exacte), puis séparées à chaque nœud
   (callback `cbCut`, `PreCrush = 1`). La borne retenue est la meilleure des deux.

**Résultats sur A_02** (900 s, départ : meilleur recuit, checker officiel : réalisable)

| | Borne | Solution | Gap certifié |
|---|---|---|---|
| Modèle seul | 2058,39 | 4672,13 (départ inchangé) | 55,94 % |
| Relaxation + coupes (351 coupes, 8 s) | 4561,96 | – | – |
| Coupes + PLNE, 300 s, sans coupes aux nœuds | 4574,58 | 4672,13 | 2,09 % |
| Coupes + PLNE, 300 s, avec coupes aux nœuds | 4582,43 | 4672,13 | 1,92 % |
| **Coupes + PLNE, 900 s** | **4610,21** | **4671,94** | **1,32 %** |

- La borne passe de 44 % à 98,7 % de la meilleure solution ; elle certifie que la meilleure valeur du
  challenge (4671,38) est à moins de 1,31 % de l'optimum.
- La PLNE améliore aussi la solution (4672,13 → 4671,94, à 0,01 % de la référence), ce qu'elle ne
  faisait pas sans les coupes.
- Solution : `solutions/A_02_plne_coupes.txt` ; log : `results/logs/A_02_plne_coupes.log` ;
  ligne `plne` / variante `coupes` dans `results.csv`. Le tableau garde la meilleure solution et la
  meilleure borne des deux variantes (marquée †).

## À faire

- [x] Modèle : variables de date de début, ressources, exclusions, linéarisation du quantile.
- [x] Campagne au temps du challenge sur les 15 instances A (voir ci-dessus).
- [x] Amélioration de la borne : coupes de quantile (`--coupes`, voir ci-dessous), testé sur A_02.
- [ ] Coupes sur les autres instances au temps limite (A_05, A_08, A_11, A_13, A_14, A_15) :
      `python src/campagne.py plne --coupes --instances A_05 A_08 A_11 A_13 A_14 A_15` (≈ 1 h 30).
