# Rapport : données à conserver et graphes

## Organisation des fichiers

```
results/
  instances.csv         caractéristiques des instances
  results.csv           une ligne par exécution
  convergence/          un CSV par exécution du recuit
solutions/              meilleures solutions (.txt, vérifiables avec le checker)
```

## Données à conserver

### 1. Caractéristiques des instances (`instances.csv`)
Pour chaque instance : nombre d'interventions, `T`, nombre de ressources, nombre d'exclusions,
nombre de scénarios (min et max), `Alpha`, `Quantile`, `ComputationTime`.
Se calcule une fois depuis les JSON.

### 2. Résultats par exécution (`results.csv`)

| Colonne | Pourquoi |
|---|---|
| instance, méthode, graine aléatoire | reproduire le résultat |
| objectif total, obj1 (risque moyen), obj2 (excès) | critère du challenge et ce qui le fait bouger |
| réalisable (oui/non), violations ressources, violations exclusions | une solution irréalisable ne compte pas |
| temps de calcul | comparer les méthodes à temps égal |
| amélioration par rapport au glouton (%) | apport de la métaheuristique |
| écart à la meilleure solution connue (%) | se situer face aux résultats publiés du challenge |
| paramètres : `a`, `b`, `c`, `λ`, `T0`, `α`, nb d'itérations | savoir quel réglage a produit quel résultat |

PLNE : ajouter la borne inférieure et le gap si le solveur les donne.

### 3. Convergence du recuit (`convergence/`)
Tous les N itérations (ou chaque seconde) : temps, itération, température, coût courant,
meilleur coût, taux d'acceptation, répartition des mouvements acceptés (déplacement / swap).

### 4. Expériences de comparaison
- **Plusieurs graines** (5 à 10) par instance pour le recuit : moyenne et écart-type.
- **Critères de tri du glouton** : tension seule, regret seul, score combiné.
- **Recuit avec / sans descente finale** : apport de chaque composant.

### 5. Solutions
La meilleure solution `.txt` de chaque instance dans `solutions/`.

## Graphes

### Comparer les méthodes
1. **Barres groupées : objectif par instance et par méthode** (glouton, recuit, PLNE).
   Afficher l'écart à la meilleure solution connue en % (l'échelle de l'objectif varie entre instances).
   *Données : `results.csv`.*
2. **Boîtes à moustaches : dispersion du recuit sur 5 à 10 graines**, une boîte par instance.
   *Données : `results.csv`.*
3. **Nuage de points : qualité selon le temps de calcul**, couleur par méthode.
   *Données : `results.csv`.*

### Comportement du recuit
4. **Courbe de convergence** : coût courant et meilleur coût en fonction du temps,
   sur 2 ou 3 instances représentatives. *Données : `convergence/`.*
5. **Température et taux d'acceptation** au fil des itérations
   (≈ 50 % au début, ≈ 0 à la fin) : justifie `T0` et `α`. *Données : `convergence/`.*
6. **Barres empilées : part déplacements / swaps** parmi les mouvements améliorants.
   *Données : `convergence/`.*

### Justifier les choix
7. **Comparaison des critères de tri du glouton** (tension, regret, combiné). *Données : `results.csv`.*
8. **Apport de chaque étape** : glouton → + recuit → + descente finale. *Données : `results.csv`.*

### Illustrer une solution (facultatif)
9. **Diagramme de Gantt** : une barre par intervention, saisons en fond.
10. **Utilisation d'une ressource dans le temps** entre ses bornes `min` et `max`.
11. **Risque par période** : moyenne et quantile τ ; la zone entre les deux est le terme d'excès.

Les graphes 9 à 11 se calculent depuis une solution et `Evaluation` (tableaux `risk` et `usage`).

**Essentiel pour le rapport : 1, 2, 4, 7 et 9.**

## À faire

- [ ] `src/logger.py` : écriture de `results.csv` et des fichiers de convergence.
- [ ] `src/graphes.py` : génération des graphes (matplotlib) depuis `results/`.
- [ ] Récupérer les meilleures solutions connues du challenge (pour l'écart en %).
