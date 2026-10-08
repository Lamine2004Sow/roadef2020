# Rapport : données à conserver et graphes

## Organisation des fichiers

```
results/
  instances.csv         caractéristiques des instances
  results.csv           une ligne par exécution
  convergence/          un CSV par exécution du recuit
  logs/                 sortie du recuit et du checker, campagne finale (non versionné)
  reglage/              réglage des paramètres : results.csv, convergence/, solutions/, synthese.csv
solutions/              solutions (.txt, vérifiables avec le checker) ; campagne : <instance>_metaheuristique_s<g>.txt
```

## Code

**`src/logger.py`**

| Fonction | Rôle |
|---|---|
| `log_instance(instance, instance_path)` | ajoute l'instance à `instances.csv` (une seule fois) |
| `log_result(ev, instance_path, methode, temps, variante, graine, **params)` | ajoute une exécution à `results.csv` ; obj1, obj2, réalisabilité et violations calculés depuis l'`Evaluation` |
| `Convergence(instance_path, methode, graine)` | fichier `convergence/<instance>_<methode>_s<graine>.csv`, une ligne par appel à `.log(...)` |
| `objectifs(ev)` | (obj1 risque moyen, obj2 excès) |
| `read_csv(path)` | relit un CSV (nombres convertis) |

Le glouton enregistre déjà chaque exécution (`methode='glouton'`, `variante='a=.. b=.. c=..'`).

**`src/graphes.py`** : `make graphes [INSTANCE=... SOLUTION=...]` → `results/figures/` (PNG + PDF).
Graphes 1 à 8 depuis `results/` (ignorés tant que les données manquent), 9 à 11 si une solution est donnée.

- Référence de l'écart (%) : `results/best_known.csv` (colonnes `instance,objectif`) s'il existe,
  sinon la meilleure solution réalisable trouvée. La série de référence est marquée « réf. ».
- Noms de méthodes reconnus (couleur fixe) : `glouton`, `recuit`, `plne`, `grasp`, `recuit+descente`, `tabou`.
- Seules les exécutions réalisables comptent dans les graphes 1, 2, 3, 7 et 8.

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

### Comparer les méthodes selon la taille
12a. **Temps selon la taille** (log-log), glouton et PLNE : leur temps est un résultat.
    Montre que la PLNE explose quand le glouton reste raisonnable. *Données : `results.csv` + `instances.csv`.*
12b. **Écart (%) selon la taille**, toutes méthodes, à temps limite égal : pour le recuit / tabou
    le temps est un paramètre (arrêt sur chrono), on compare donc la qualité. *Mêmes données.*
13. **Profil de performance (Dolan-Moré)** : pour chaque méthode, part des instances où elle est
    à moins de x % de la meilleure. Résume la comparaison finale en une figure. *Données : `results.csv`.*

Taille d'une instance (colonne `taille` de `instances.csv`, `logger.taille`) : nombre de valeurs de
risque `Σᵢ Σₛ Σ_{t où i est en cours} S_t` (≈ `Σᵢ Σₛ Δᵢ(s) × nombre moyen de scénarios`), de 2 577 (A_09)
à 17,6 M (A_05) ; proche du nombre de non-zéros de la PLNE. Le nombre d'interventions seul n'explique
pas le temps (A_04 : 85 s pour le glouton).

Lecture (`results/figures/12a_temps_taille`, `12b_ecart_taille`, `13_profil_performance`) :
- 12a : la PLNE prouve l'optimum en quelques secondes jusqu'à ≈ 1,5·10⁵ (et A_04, 1 scénario, en 112 s),
  puis atteint le temps limite dès 2·10⁵ ; le glouton reste sous 10 s sauf A_04.
- 12b : marqueurs creux = instances de réglage ; trait du recuit = meilleure → pire graine.
  Les écarts du recuit et de la PLNE ne croissent pas avec la taille : ils dépendent surtout du nombre
  de scénarios et des violations à réparer par le glouton (A_14, A_15).
- 13 : sur les 12 instances hors réglage seulement. La PLNE est toujours la meilleure par construction
  (elle part de la meilleure graine du recuit) ; la meilleure graine est à moins de 0,4 % de la meilleure
  méthode partout, la moyenne des graines à moins de 0,9 %, le glouton jusqu'à 10 %.

**Essentiel pour le rapport : 1, 2, 4, 7, 9 et 13.**

## Protocole de comparaison

### Étape 1 : choix de la métaheuristique (recuit ou tabou)
- Sur un **sous-ensemble d'instances** (4 ou 5, A et B, tailles variées), distinct de celui
  de la comparaison finale : régler et choisir sur les instances de test biaise le résultat.
- **À temps égal**, 5 à 10 graines chacune.
- Critères : écart moyen à la référence, stabilité (écart-type entre graines), taux de réalisabilité.
- Rapport : courte section avec les graphes 2 et 4 pour les deux métaheuristiques.

### Étape 2 : comparaison glouton / métaheuristique retenue / PLNE
- **Même budget de temps** (`ComputationTime` du challenge) pour la métaheuristique et la PLNE ;
  le glouton tourne une fois, on note son temps.
- **Même machine, même évaluation** (checker officiel).
- Métaheuristique : 5 graines (campagne finale), moyenne ± écart-type et meilleure valeur.
- PLNE : solution, borne inférieure et gap ; un optimum prouvé sert de référence exacte.

| Indicateur | Ce qu'il montre |
|---|---|
| écart à la meilleure solution connue (%) | qualité |
| taux de solutions réalisables | fiabilité |
| temps (glouton, PLNE) / temps pour atteindre la qualité du glouton (méta) | vitesse |
| gap de la PLNE | distance prouvée à l'optimum |

**Présentation**
- Tableau principal, une ligne par instance, généré par `src/tableau.py` (`make tableau`) →
  `results/tableau.md` : glouton (obj, temps) | méta (moyenne ± écart-type, meilleure) |
  PLNE (obj, borne, gap certifié, temps), écart à la référence du challenge dans chaque case ;
  les 3 instances de réglage du recuit (A_06, A_09, A_13) en bloc séparé, avec leur propre moyenne.
- Graphes 1, 12a, 12b et 13.
- Optionnel : test de Wilcoxon apparié méta vs glouton sur toutes les instances.

**Conclusion attendue** : rôles complémentaires plutôt qu'un gagnant — glouton rapide (point de
départ), métaheuristique meilleur compromis, PLNE référence exacte sur les petites instances.

## À faire

- [x] `src/logger.py` : écriture de `results.csv` et des fichiers de convergence.
- [x] `src/graphes.py` : génération des graphes (matplotlib) depuis `results/`.
- [x] Brancher `Convergence` et `log_result` dans le recuit (méthodes `recuit` et `recuit+descente`, graines).
- [x] Récupérer les meilleures solutions connues du challenge : `results/best_known.csv`
  (qualification, 15 min, [roadef.org](https://roadef.org/challenge/2020/en/qualifresult.php)).
- [x] Colonne `taille` dans `instances.csv` (+ recalcul des instances déjà enregistrées).
- [x] Graphes 12a, 12b (taille) et 13 (profil de performance), données de `src/tableau.py`.
- [x] Colonnes PLNE dans `results.csv` : borne inférieure et gap.
- [x] Campagne PLNE au temps du challenge (`python src/campagne.py plne`, voir `notes/plne.md`).
- [x] Tableau principal : `results/tableau.md` et `.csv` (`make tableau`), instances de réglage à part.
- [x] Choisir le sous-ensemble d'instances de réglage : A_06, A_09, A_13 (voir `notes/meta_heuristique.md`).
  Elles restent dans la campagne finale : tableaux séparés dans `notes/meta_heuristique.md`,
  marquées d'un * dans les graphes 1, 2 et 8.
- [x] Campagne finale du recuit : 15 instances A × 5 graines au temps du challenge (`src/campagne.py`).
