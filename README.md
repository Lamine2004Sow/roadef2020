# ROADEF/EURO Challenge 2020 — Planification de la maintenance (RTE)

Planification des interventions de maintenance du réseau électrique RTE : choisir la date de début
de chaque intervention en respectant les contraintes de ressources (bornes min/max) et d'exclusion,
tout en minimisant un risque combinant moyenne et excès au quantile τ sur plusieurs scénarios.

## Approche

1. **Heuristique gloutonne** : interventions triées de la plus difficile à la plus facile
   (tension sur les ressources, exclusions, regret), puis placées une à une à la date qui augmente
   le moins le coût.
2. **Métaheuristique** : recuit simulé partant de la solution gloutonne, avec deux mouvements
   (déplacement d'une intervention, swap des dates de deux interventions), suivi d'une descente locale.
3. **PLNE** : modèle exact avec Gurobi (seule méthode qui en dépend).

Le détail des stratégies est dans [`notes/`](notes/).

## Structure

```
src/
  reader.py            lecture d'une instance JSON
  writer.py            écriture d'une solution (.txt)
  indicateurs.py       indicateurs par intervention et tri du glouton
  evaluation.py        coût incrémental (objectif + pénalité des contraintes violées)
  heuristique.py       glouton + réparation des violations
  meta_heuristique.py  recuit simulé + descente
  campagne.py          réglage des paramètres et campagne finale (plusieurs graines)
  logger.py            enregistrement des résultats (results/)
  graphes.py           graphes du rapport (results/figures/)
  Plne.py              PLNE complète (Gurobi)
notes/
  heuristique.md       stratégie du glouton
  meta_heuristique.md  stratégie du recuit simulé
  plne.md              modèle PLNE complet, dépendance à Gurobi, premiers résultats
  bibliographie.md     sources extérieures (sujet, checker, meilleures valeurs, articles)
  rapport.md           données et graphes pour le rapport
solutions/             solutions produites
RTE_ChallengeROADEF2020_checker.py   checker officiel
Makefile                             commandes (install, heuristique, metaheuristique, plne, check, clean)
```

## Installation

```bash
make install
```

`make install` crée un environnement virtuel `.venv` et y installe les versions figées de
`requirements.txt` ; les commandes `make` l'utilisent automatiquement.

**Gurobi** n'est nécessaire que pour la PLNE, avec une **licence complète** (licence académique
gratuite, fichier indiqué par `GRB_LICENSE_FILE`). La licence fournie par `pip install gurobipy`
est limitée à 2000 variables : dans ce cas, ou sans Gurobi, `make plne` s'arrête avec un message
explicite. Le glouton et le recuit fonctionnent sans Gurobi.

Les instances (`A_set/`, `B_set/`) ne sont pas versionnées (≈ 10 Go) : les télécharger depuis le site
du challenge et les placer à la racine (`A_set/A_01.json`, `B_set/B_set_rounded/B_01.json`, …).

## Résoudre une instance

```bash
make heuristique     INSTANCE=A_set/A_01.json   # -> solutions/A_01_heuristique.txt
make metaheuristique INSTANCE=A_set/A_01.json   # -> solutions/A_01_metaheuristique.txt
make plne            INSTANCE=A_set/A_01.json   # -> solutions/A_01_plne.txt
```

Chaque commande écrit la solution puis la vérifie avec le checker officiel.
`src/heuristique.py`, `src/meta_heuristique.py` et `src/Plne.py` prennent en arguments `<instance.json> <solution.txt>`.

## Campagnes d'expériences

```bash
.venv/bin/python src/campagne.py reglage [--temps 120] [--jobs 6]            # -> results/reglage/synthese.csv
.venv/bin/python src/campagne.py finale  [--graines 1 2 3 4 5] [--jobs 6]    # 15 instances A, 15 min chacune
```

La campagne finale (≈ 3 h 30 sur 6 cœurs) écrit `solutions/<instance>_metaheuristique_s<g>.txt`,
vérifie chaque solution avec le checker et ajoute les résultats à `results/results.csv`.
Paramètres du recuit : `--param nom=valeur` (voir `PARAMS` dans `src/meta_heuristique.py`).
Résultats et réglage : `notes/meta_heuristique.md`.

## Vérifier une solution

```bash
make check INSTANCE=A_set/A_01.json                     # solution par défaut : solutions/A_01.txt
make check INSTANCE=A_set/A_01.json SOLUTION=sol.txt
```

`make help` liste les commandes disponibles.

Format d'une solution : une ligne `nom_intervention date_début` par intervention.
