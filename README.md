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
3. **PLNE** : modèle exact avec Gurobi.

Le détail des stratégies est dans [`notes/`](notes/).

## Structure

```
src/
  reader.py            lecture d'une instance JSON
  writer.py            écriture d'une solution (.txt)
  indicateurs.py       indicateurs par intervention et tri du glouton
  evaluation.py        coût incrémental (objectif + pénalité des contraintes violées)
  heuristique.py       glouton                       (en cours)
  meta_heuristique.py  recuit simulé + descente      (en cours)
  Plne.py              modèle PLNE                   (en cours)
notes/
  heuristique.md       stratégie du glouton
  meta_heuristique.md  stratégie du recuit simulé
  rapport.md           données et graphes pour le rapport
solutions/             solutions produites
RTE_ChallengeROADEF2020_checker.py   checker officiel
Makefile                             commandes (install, heuristique, metaheuristique, check, clean)
```

## Installation

```bash
make install
```

Les instances (`A_set/`, `B_set/`) ne sont pas versionnées (≈ 10 Go) : les télécharger depuis le site
du challenge et les placer à la racine (`A_set/A_01.json`, `B_set/B_set_rounded/B_01.json`, …).

## Résoudre une instance

```bash
make heuristique     INSTANCE=A_set/A_01.json   # -> solutions/A_01_heuristique.txt
make metaheuristique INSTANCE=A_set/A_01.json   # -> solutions/A_01_metaheuristique.txt
```

Chaque commande écrit la solution puis la vérifie avec le checker officiel.
`src/heuristique.py` et `src/meta_heuristique.py` prennent en arguments `<instance.json> <solution.txt>`.

## Vérifier une solution

```bash
make check INSTANCE=A_set/A_01.json                     # solution par défaut : solutions/A_01.txt
make check INSTANCE=A_set/A_01.json SOLUTION=sol.txt
```

`make help` liste les commandes disponibles.

Format d'une solution : une ligne `nom_intervention date_début` par intervention.
