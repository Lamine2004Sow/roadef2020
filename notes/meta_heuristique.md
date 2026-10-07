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

Le glouton (`heuristique.py`) n'est pas encore codé.
`meta_heuristique.py` est vide. Le checker officiel sert à valider la solution finale.

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
- [ ] Mouvements déplacement et swap.
- [ ] Boucle du recuit + calibrage de `T0`.
- [ ] Descente finale.
