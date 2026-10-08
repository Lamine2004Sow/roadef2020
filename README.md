# ROADEF/EURO Challenge 2020 — Planification de la maintenance (RTE)

Planification des interventions de maintenance du réseau de transport d'électricité de RTE : choisir
la date de début de chaque intervention en respectant les ressources (bornes min/max par période) et
les exclusions saisonnières, tout en minimisant un risque incertain décrit par des scénarios
(moyenne du risque + excès du quantile τ sur cette moyenne).

Trois méthodes, évaluées sur les 15 instances A au temps du challenge (15 min par instance) :

1. **Glouton** : interventions triées de la plus difficile à la plus facile (tension sur les
   ressources, exclusions, regret), placées une à une à la date qui augmente le moins le coût,
   puis réparation des violations.
2. **Recuit simulé + descente** : part du glouton ; déplacements (locaux ±5 ou globaux) et swaps
   de dates ; température calibrée sur l'objectif, refroidissement ajusté au temps limite.
3. **PLNE** (Gurobi) : modèle exact, quantile linéarisé par big-M, départ depuis le meilleur recuit ;
   option `--coupes` : coupes de quantile qui renforcent fortement la borne inférieure.

## Résultats

Écart à la meilleure valeur de la qualification du challenge ([roadef.org](https://roadef.org/challenge/2020/en/qualifresult.php),
`results/best_known.csv`). Recuit : 5 graines par instance, **75/75 exécutions réalisables** ;
toutes les solutions sont validées par le checker officiel.

Les paramètres du recuit ont été réglés sur **A_06, A_09 et A_13** : ces trois instances sont
présentées à part, et les conclusions portent sur les douze autres.

| Écart moyen à la référence | Glouton | Recuit (moyenne) | Recuit (meilleure graine) | PLNE | Gap certifié moyen |
|---|---:|---:|---:|---:|---:|
| **12 instances hors réglage** | 2,83 % | **0,52 %** | 0,39 % | 0,35 % | 3,45 % |
| 3 instances de réglage | 4,83 % | 0,63 % | 0,23 % | 0,003 % | 0,008 % |

- Le recuit divise par plus de cinq l'écart du glouton ; la meilleure graine atteint la référence
  sur 6 instances et en est à moins de 0,1 % sur 5 autres.
- Le réglage n'a pas avantagé ses propres instances (0,63 % contre 0,52 %).
- La PLNE **prouve l'optimum de 8 instances** (A_01, A_03, A_04, A_06, A_07, A_09, A_10, A_12),
  toutes égales à la référence ; elle améliore le meilleur recuit jusqu'à l'optimum sur A_01, A_04, A_06.
- **Coupes de quantile** sur A_02 : gap certifié de **55,94 % → 1,32 %** (borne 2058 → 4610), et
  meilleure solution 4672,13 → 4671,94.

<details>
<summary>Détail par instance</summary>

Écart à la référence (**0** : référence atteinte). σ : écart-type de l'objectif sur les 5 graines.
† : borne obtenue avec `--coupes`.

**Instances hors réglage**

| Instance | Référence | Glouton | Recuit, moyenne | σ | Recuit, meilleure | PLNE | Gap certifié |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_01 | 1767,82 | 2,26 % | 0,11 % | 0,73 | 0,08 % | **0** | optimal |
| A_02 | 4671,38 | 0,29 % | 0,05 % | 1,09 | 0,02 % | 0,01 % | 1,32 % † |
| A_03 | 848,18 | 0,31 % | 0,18 % | 1,32 | **0** | **0** | optimal |
| A_04 | 2085,88 | 4,21 % | 0,84 % | 6,20 | 0,36 % | **0** | optimal |
| A_05 | 635,22 | 0,73 % | 0,12 % | 0,53 | 0,02 % | 0,02 % | 6,59 % |
| A_07 | 2272,78 | **0** | **0** | 0 | **0** | **0** | optimal |
| A_08 | 744,29 | 0,21 % | **0** | 0 | **0** | **0** | 5,94 % |
| A_10 | 2994,85 | 0,08 % | 0,004 % | 0,16 | **0** | **0** | optimal |
| A_11 | 495,26 | 1,29 % | 0,04 % | 0,20 | 0,003 % | 0,002 % | 7,00 % |
| A_12 | 789,63 | 0,30 % | 0,01 % | 0,18 | **0** | **0** | optimal |
| A_14 | 2264,12 | 12,06 % | 2,54 % | 9,13 | 2,14 % | 2,13 % | 10,05 % |
| A_15 | 2268,57 | 12,28 % | 2,41 % | 17,03 | 2,04 % | 2,04 % | 10,53 % |

**Instances de réglage**

| Instance | Référence | Glouton | Recuit, moyenne | σ | Recuit, meilleure | PLNE | Gap certifié |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_06 | 590,62 | 8,55 % | 1,80 % | 7,31 | 0,69 % | **0** | optimal |
| A_09 | 1507,28 | 5,23 % | **0** | 0 | **0** | **0** | optimal |
| A_13 | 1998,66 | 0,70 % | 0,09 % | 1,35 | 0,02 % | 0,009 % | 0,02 % |

Temps : glouton < 10 s (sauf A_04 : 85 s) ; PLNE optimale en moins de 3 s sur les petites instances,
112 s sur A_04, temps limite (900 s) dès 12 scénarios ou plus.

</details>

Machine : Intel Core i7-1185G7 (4 cœurs / 8 fils), 15 Go de RAM, Python 3.12, Gurobi 13.0.
Le rapport complet (LaTeX), les notes, les figures, les journaux et les solutions des campagnes sont
archivés hors du dépôt.

## Structure

```
src/
  reader.py            lecture d'une instance JSON
  writer.py            écriture d'une solution (.txt)
  evaluation.py        coût incrémental (objectif + pénalité des contraintes violées), identique au checker
  indicateurs.py       indicateurs par intervention et score de difficulté du glouton
  heuristique.py       glouton + réparation des violations
  meta_heuristique.py  recuit simulé + descente
  Plne.py              PLNE complète (Gurobi), option --coupes
  campagne.py          campagnes : réglage, finale (plusieurs graines), PLNE
  logger.py            enregistrement des résultats (results/)
  tableau.py           tableau comparatif glouton / recuit / PLNE (results/tableau.md, .csv, .tex)
  graphes.py           figures (results/figures/)
results/best_known.csv               meilleures valeurs du challenge (référence des écarts)
RTE_ChallengeROADEF2020_checker.py   checker officiel
Makefile                             commandes (make help)
```

Les sorties (`solutions/`, `results/`) sont créées par les commandes et ne sont pas versionnées.

## Installation

```bash
make install
```

Crée un environnement virtuel `.venv` avec les versions figées de `requirements.txt` ; les commandes
`make` l'utilisent automatiquement.

**Gurobi** n'est nécessaire que pour la PLNE, avec une **licence complète** (licence académique
gratuite, fichier indiqué par `GRB_LICENSE_FILE`). La licence fournie par `pip install gurobipy` est
limitée à 2000 variables : dans ce cas, ou sans Gurobi, `make plne` s'arrête avec un message explicite.
Le glouton et le recuit fonctionnent sans Gurobi.

Les instances (`A_set/`, `B_set/`, ≈ 10 Go) ne sont pas versionnées : les télécharger depuis le
[dépôt du challenge](https://github.com/rte-france/challenge-roadef-2020) et les placer à la racine
(`A_set/A_01.json`, `B_set/B_set_rounded/B_01.json`, …).

## Résoudre une instance

```bash
make heuristique     INSTANCE=A_set/A_01.json               # -> solutions/A_01_heuristique.txt
make metaheuristique INSTANCE=A_set/A_01.json [TEMPS=60]    # -> solutions/A_01_metaheuristique.txt
make plne            INSTANCE=A_set/A_01.json [DEPART=sol]  # -> solutions/A_01_plne.txt
```

Chaque commande écrit la solution puis la vérifie avec le checker officiel. Temps par défaut :
`ComputationTime` de l'instance (15 min). PLNE avec coupes :
`.venv/bin/python src/Plne.py A_set/A_02.json sol.txt --depart depart.txt --coupes`.

## Reproduire les résultats

```bash
.venv/bin/python src/campagne.py finale                 # recuit : 15 instances A × graines 1 à 5 (≈ 3 h 30, 6 cœurs)
.venv/bin/python src/campagne.py plne [--memoire 8]     # PLNE, départ : meilleur recuit (≈ 2 h)
.venv/bin/python src/campagne.py plne --coupes --instances A_02
.venv/bin/python src/campagne.py reglage                # réglage OFAT sur A_06, A_09, A_13 (120 s, graines 100-101)
make tableau                                            # results/tableau.md, .csv, .tex
make graphes                                            # results/figures/
```

Les campagnes vérifient chaque solution avec le checker et ajoutent une ligne par exécution à
`results/results.csv`. Paramètres du recuit : `--param nom=valeur` (voir `PARAMS` dans
`src/meta_heuristique.py` ; valeurs par défaut conservées après réglage).

## Vérifier une solution

```bash
make check INSTANCE=A_set/A_01.json SOLUTION=solutions/A_01_plne.txt
```

Format d'une solution : une ligne `nom_intervention date_début` par intervention.

## Références

- Sujet, instances et checker : [rte-france/challenge-roadef-2020](https://github.com/rte-france/challenge-roadef-2020).
- G. Gouvine, *Mixed-Integer Programming decomposition for stochastic programming with quantiles*,
  [arXiv:2111.01047](https://arxiv.org/abs/2111.01047) (comparaison de la PLNE).
- S. Kirkpatrick, C. D. Gelatt, M. P. Vecchi, *Optimization by Simulated Annealing*, Science, 1983.
