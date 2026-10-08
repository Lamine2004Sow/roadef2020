# Métaheuristique : recuit simulé + recherche locale

Fichier : `src/meta_heuristique.py`

## Principe

1. **Départ** : solution du glouton (voir `heuristique.md`).
2. **Recuit simulé** avec deux mouvements :
   - **Déplacement** : une intervention change de date de début
     (souvent un `t` proche, ±1 à ±5, parfois un `t` aléatoire pour diversifier).
   - **Swap** (remplace le 2-opt) : deux interventions qui se recouvrent échangent leurs dates,
     si chacune reste dans `[1, tmax]`.
3. **Acceptation** : toujours si `Δ < 0`, sinon avec probabilité `exp(−Δ / T)`.
4. **Descente finale** : swaps et déplacements améliorants uniquement, jusqu'au minimum local.

## Fonctions utiles déjà présentes dans `src/`

| Fonction | Fichier | Rôle dans la métaheuristique |
|---|---|---|
| `read_instance(path)` | `reader.py` | charge l'instance |
| `start_candidates(intervention, horizon)` | `reader.py` | dates autorisées → tirage d'une nouvelle date pour un déplacement, validité d'un swap |
| `duration(intervention, start)` | `reader.py` | périodes touchées par un mouvement (avant et après) → zone à recalculer pour le Δ |
| `write_solution(path, starts)` | `writer.py` | écriture de la meilleure solution |
| `Evaluation(instance, lam)` | `evaluation.py` | état + coût incrémental (voir ci-dessous) |

Le checker officiel sert à valider la solution finale.

## Pourquoi pas un vrai 2-opt

Le 2-opt vient du TSP (inverser un morceau de tournée). Ici une solution est une affectation
`intervention → date de début`, pas un ordre : le swap en est l'équivalent direct.

## Points clés

- **Évaluation incrémentale du Δ** : ne recalculer que les périodes touchées par le mouvement
  (risque par scénario, puis quantile). Fonction partagée par les trois étapes — à coder en premier.
- **Infaisabilité** : autoriser les violations avec une pénalité `coût + λ × violations`, `λ` croissant.
- **Température** : `T0` calibrée pour accepter ~50 % des mouvements dégradants au départ
  (mesurée sur quelques centaines de mouvements aléatoires), puis `T ← α·T` avec `α ≈ 0,999`.
- **Temps limite** : arrêt sur chrono (`ComputationTime` de l'instance), renvoyer la **meilleure**
  solution trouvée, pas la courante.

## Évaluation incrémentale (`src/evaluation.py`)

`coût = objectif + λ · (violations ressources + périodes d'exclusion violées)`, objectif identique au checker.

| Méthode | Rôle |
|---|---|
| `assign({i: s, ...})` | applique le changement (`s=None` = retrait), renvoie Δ coût |
| `delta({i: s, ...})` | Δ coût sans modifier l'état (applique puis annule) |
| `swap_changes(i, j)` | changements d'un swap, `None` si une date sort de `[1, tmax]` |
| `can_start(i, s)` | date autorisée pour `i` |
| `objective()`, `violation()`, `cost()` | valeurs courantes |
| `set_lambda(lam)` | change le poids de la pénalité |
| `start` | dict `{intervention: date}` de la solution courante |

Usage recuit (évite l'aller-retour de `delta`) :
```python
old = {i: ev.start.get(i) for i in changes}
d = ev.assign(changes)
if not accepte(d):
    ev.assign(old)
```

Vérifié contre le checker (A_01, A_05, B_01) : objectif et violations identiques, pas de dérive
après 500 mouvements. Environ 2000 à 3000 essais par seconde en Python.

## À faire

- [x] Évaluation incrémentale du Δ.
- [x] Mouvements déplacement et swap.
- [x] Boucle du recuit + calibrage de `T0`.
- [x] Descente finale.
- [x] Régler les paramètres sur les instances de réglage (voir « Réglage des paramètres »).
- [x] Lancer avec le temps limite du challenge et plusieurs graines (voir « Résultats au temps du challenge »).

## Implémentation (`src/meta_heuristique.py`)

`make metaheuristique INSTANCE=... [TEMPS=60] [GRAINE=0]` (temps par défaut : `ComputationTime` de l'instance, en minutes).

Options en ligne de commande : `--param nom=valeur` (répétable) remplace une valeur de `PARAMS`, enregistrée dans la
colonne `variante` ; `--resultats DOSSIER` écrit `results.csv` et `convergence/` ailleurs que dans `results/`.

| Fonction | Rôle |
|---|---|
| `Recuit.voisin` | swap (30 %) ou déplacement local ±5 (80 % des déplacements) / global |
| `Recuit.calibrer_t0` | `T0 = −Δ̄ / ln 0,5`, Δ̄ sur les mouvements **sans changement de violation** |
| `Recuit.run` | paliers de `|I|` itérations, `α` déduit du temps limite (`T_final = 10⁻³ T0`), `λ ×1,01` tant qu'infaisable |
| `descente` | meilleurs déplacements puis swaps entre interventions qui se chevauchent ; refuse toute hausse des violations |
| `cle` | ordre des solutions : violations d'abord, puis objectif (indépendant de λ) |

Répartition du temps : glouton (réparation bornée à 20 % du temps), recuit jusqu'à 90 %, descente le reste.
Enregistre `recuit` et `recuit+descente` dans `results.csv` et la convergence dans `results/convergence/`.

**Piège rencontré** : calibrer `T0` sur tous les Δ positifs donnait une température dominée par la
pénalité (λ ≈ 10⁵) : le recuit marchait au hasard et n'améliorait jamais le glouton.

## Premiers résultats (60 s, graine 0)

| Instance | Glouton | Recuit | + Descente |
|---|---|---|---|
| A_01 | 1807.83 | 1771.10 | **1770.65** (−2,1 %) |
| A_05 | 639.87 | 637.81 | **637.67** (−0,3 %) |
| B_01 | 4200.76 (viol. 0,14) | 4099.39 (réalisable) | **4099.39** |

Le recuit termine la réparation de B_01, que le glouton ne réussissait pas.

## Réglage des paramètres (`python src/campagne.py reglage`)

Un facteur à la fois autour de `PARAMS`, sur **A_06, A_09, A_13** (tailles et écarts glouton / meilleur
connu variés), graines 100 et 101, **120 s** par exécution, 6 exécutions en parallèle.
Critère : écart moyen (%) au meilleur objectif trouvé pendant le réglage. Synthèse : `results/reglage/synthese.csv`.

| Variante | Moyenne | A_06 | A_09 | A_13 |
|---|---|---|---|---|
| ratio_final=1e-4 | 0,36 % | 1,04 % | 0 | 0,05 % |
| p_swap=0,5 | 0,58 % | 1,65 % | 0 | 0,08 % |
| **défaut** | 0,69 % | 1,77 % | 0 | 0,31 % |
| p0=0,8 | 0,86 % | 2,48 % | 0 | 0,09 % |
| p0=0,2 | 0,96 % | 2,84 % | 0 | 0,05 % |
| r=2 | 1,06 % | 3,08 % | 0 | 0,10 % |
| p_loc=0,95 | 1,24 % | 3,67 % | 0 | 0,07 % |
| r=10 | 1,26 % | 3,72 % | 0 | 0,07 % |
| ratio_final=1e-2 | 1,39 % | 3,91 % | 0 | 0,26 % |
| p_loc=0,5 | 1,51 % | 4,45 % | 0 | 0,08 % |
| p_swap=0,15 | 1,70 % | 5,07 % | 0 | 0,05 % |
| p_swap=0 | 2,03 % | 5,70 % | 0 | 0,38 % |

Validation des meilleures combinaisons (4 graines, 100 à 103, 120 s), objectif moyen :

| Configuration | A_06 | A_13 |
|---|---|---|
| **défaut** | **614,3** | 2003,4 |
| p_swap=0,5 + ratio_final=1e-4 | 620,5 | 2005,7 |
| p_swap=0,7 + ratio_final=1e-4 | 617,3 | **2000,2** |

**Conclusion** : les valeurs par défaut sont conservées.
- Les écarts entre configurations (< 1 %) sont du même ordre que la variation entre graines
  (défaut sur A_06 : 599 à 624) ; le classement du premier tableau tenait à deux graines favorables.
- Seul effet net : **les swaps sont nécessaires** (sans swap, A_06 ≈ 633 en moyenne contre 614).
- A_09 ne discrimine pas : toutes les variantes atteignent 1507,28.
- Limites : 2 à 4 graines, 120 s au lieu de 900 s ; les instances de réglage font aussi partie de
  l'évaluation finale (à signaler, ou les présenter à part).

## Résultats au temps du challenge (`python src/campagne.py finale`)

15 instances A × graines 1 à 5, `ComputationTime` = 15 min (hors lecture du JSON), paramètres par défaut,
6 exécutions en parallèle sur 8 cœurs. **75/75 réalisables** selon le checker officiel, dont l'objectif
coïncide avec `Evaluation` (écart max 3·10⁻⁹). Solutions : `solutions/<instance>_metaheuristique_s<g>.txt`.

Référence : meilleure valeur trouvée pendant la qualification du challenge (15 min), relevée sur
[roadef.org](https://roadef.org/challenge/2020/en/qualifresult.php) → `results/best_known.csv`.
Écarts (%) à cette référence. A_06, A_09 et A_13 ont servi au réglage : ils sont présentés à part.

**Instances hors réglage (12)**

| Instance | Référence | Glouton | Meilleur | Moyenne ± écart-type | Écart glouton | Écart meilleur | Écart moyen |
|---|---|---|---|---|---|---|---|
| A_01 | 1767,82 | 1807,83 | 1769,24 | 1769,81 ± 0,73 | 2,26 % | 0,08 % | 0,11 % |
| A_02 | 4671,38 | 4685,07 | 4672,13 | 4673,54 ± 1,09 | 0,29 % | 0,02 % | 0,05 % |
| A_03 | 848,18 | 850,80 | **848,18** | 849,67 ± 1,32 | 0,31 % | 0 | 0,18 % |
| A_04 | 2085,88 | 2173,63 | 2093,37 | 2103,37 ± 6,20 | 4,21 % | 0,36 % | 0,84 % |
| A_05 | 635,22 | 639,87 | 635,37 | 636,01 ± 0,53 | 0,73 % | 0,02 % | 0,12 % |
| A_07 | 2272,78 | **2272,78** | **2272,78** | 2272,78 ± 0 | 0 | 0 | 0 |
| A_08 | 744,29 | 745,83 | **744,29** | 744,29 ± 0 | 0,21 % | 0 | 0 |
| A_10 | 2994,85 | 2997,25 | **2994,85** | 2994,97 ± 0,16 | 0,08 % | 0 | 0,004 % |
| A_11 | 495,26 | 501,62 | 495,27 | 495,44 ± 0,20 | 1,29 % | 0,003 % | 0,04 % |
| A_12 | 789,63 | 792,00 | **789,63** | 789,73 ± 0,18 | 0,30 % | 0 | 0,01 % |
| A_14 | 2264,12 | 2537,23 | 2312,69 | 2321,53 ± 9,13 | 12,06 % | 2,15 % | 2,54 % |
| A_15 | 2268,57 | 2547,18 | 2314,94 | 2323,28 ± 17,03 | 12,28 % | 2,04 % | 2,41 % |
| **Moyenne** | | | | | 2,83 % | 0,39 % | 0,53 % |

**Instances de réglage (3)**

| Instance | Référence | Glouton | Meilleur | Moyenne ± écart-type | Écart glouton | Écart meilleur | Écart moyen |
|---|---|---|---|---|---|---|---|
| A_06 | 590,62 | 641,15 | 594,69 | 601,23 ± 7,31 | 8,55 % | 0,69 % | 1,80 % |
| A_09 | 1507,28 | 1586,19 | **1507,28** | 1507,28 ± 0 | 5,23 % | 0 | 0 |
| A_13 | 1998,66 | 2012,72 | 1999,00 | 2000,53 ± 1,35 | 0,70 % | 0,02 % | 0,09 % |
| **Moyenne** | | | | | 4,83 % | 0,24 % | 0,63 % |

En gras : référence atteinte (écart < 0,001 %).

- Référence atteinte sur 6 instances (A_03, A_07, A_08, A_09, A_10, A_12), à moins de 0,1 % sur 5 autres.
- Hors réglage, l'écart moyen passe de 2,83 % (glouton) à 0,53 % (moyenne des graines) : le réglage
  n'a pas favorisé ses propres instances (0,63 %), cohérent avec le choix des valeurs par défaut.
- Points faibles : A_14 et A_15 (≈ 2 %), où le glouton partait de 12 % ; A_04 et A_06, les plus dispersés.
- Gains sur le glouton les plus forts sur A_14 et A_15 (−9 %), où le glouton devait réparer des violations.
- Petites instances (A_07 à A_09) : même résultat pour toutes les graines.
- A_04, A_06, A_14, A_15 : écart-type de 6 à 17, plusieurs graines utiles.
