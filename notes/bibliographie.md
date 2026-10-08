# Bibliographie et sources

Tout ce qui, dans le projet, vient d'une source extérieure, et où cela sert. Le reste (glouton,
réparation, recuit, évaluation incrémentale, modèle PLNE) a été écrit pour le projet ; les idées
générales (recuit simulé, linéarisation d'un quantile par variables binaires) sont des techniques
classiques citées en section 3.

## 1. Challenge ROADEF/EURO 2020 (données, sujet, référence)

[1] P. Tournebise, M. Ruiz, P. Pancia (RTE). *ROADEF Challenge RTE: Grid operation-based outage
    maintenance planning*, sujet du challenge ROADEF/EURO 2020.
    https://github.com/rte-france/challenge-roadef-2020/raw/master/Challenge_Subject.pdf
    → définition du problème : ressources, exclusions, saisons, objectif (risque moyen et excès du
      quantile), utilisée dans `src/evaluation.py` et `src/Plne.py`.

[2] RTE, dépôt officiel du challenge : https://github.com/rte-france/challenge-roadef-2020
    et site du challenge : https://www.roadef.org/challenge/2020/en/ (pages *Subject*, *Instances and Checker*).
    → instances `A_set/`, `B_set/` (non versionnées) et **checker officiel**
      `RTE_ChallengeROADEF2020_checker.py` (fourni par les organisateurs, sert de juge pour toutes les solutions).

[3] ROADEF/EURO Challenge 2020, *Qualification results* :
    https://roadef.org/challenge/2020/en/qualifresult.php (consulté le 2026-10-08).
    → `results/best_known.csv` : meilleure valeur trouvée par les équipes sur les instances A
      (colonne « 15 min », identique à la colonne « 90 min ») ; référence des écarts (%) dans
      `notes/meta_heuristique.md`, `notes/plne.md` et les graphes 1, 2, 3 et 8.

## 2. Littérature sur le problème

[4] G. Gouvine. *Mixed-Integer Programming decomposition for stochastic programming with quantiles*,
    arXiv:2111.01047v2 [math.OC], mars 2023. https://arxiv.org/abs/2111.01047
    → **comparaison de la PLNE** (`notes/plne.md`). Méthodes nommées dans l'article :
      - *Full* : modèle PLNE d'origine, quantile avec *indicator constraints* (proche de notre
        modèle, qui utilise des big-M) ;
      - *Full+Sep*, *Full+Subs* : *Full* renforcé par des plans coupants ou des contraintes de sous-ensembles ;
      - *CGen* (et variantes) : génération de contraintes sur les scénarios, meilleure borne.
      Conditions : CPLEX 12.9, 1 h hors création du modèle, 4 cœurs, 10 Go.
      Chiffres repris : gap d'optimalité (tableau 1) de *Full* = 6,31 % sur A_08, 8,72 % sur A_11,
      12,78 % sur A_15 ; écart solution / meilleure valeur du challenge (tableau 3) de *Full* sur
      A_15 = 5,74 % ; huit instances A résolues à l'optimum par tous leurs modèles.
    → Piste d'amélioration de la borne de notre PLNE (génération de contraintes).

## 3. Méthodes générales

[5] S. Kirkpatrick, C. D. Gelatt, M. P. Vecchi. *Optimization by Simulated Annealing*.
    Science 220(4598), 671–680, 1983. doi:10.1126/science.220.4598.671
    → principe du recuit simulé (`src/meta_heuristique.py`) : acceptation `exp(−Δ/T)`,
      refroidissement géométrique `T ← α T`.

[6] Gurobi Optimization, LLC. *Gurobi Optimizer Reference Manual*. https://docs.gurobi.com
    → solveur et paramètres de la PLNE (`TimeLimit`, `MIPGap`, `Threads`, MIP start via `Start`) ;
      licence académique.

## 4. Logiciels

- Python, NumPy (calculs vectorisés de `src/evaluation.py`), Matplotlib (`src/graphes.py`),
  gurobipy ; versions figées dans `requirements.txt`.

## Ce qui n'est pas repris

- À notre connaissance, aucune ligne de code ne vient d'une solution publiée par une équipe du challenge
  (à confirmer pour le code écrit avant la mise en place de cette bibliographie).
- Les paramètres du recuit ont été choisis par notre propre réglage (`notes/meta_heuristique.md`),
  pas repris d'un article.
