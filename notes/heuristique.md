# Heuristique : glouton trié

Fichiers : `src/heuristique.py` (glouton), `src/indicateurs.py` (tri)

## Principe

1. Trier les interventions de la plus difficile à la plus facile (`sort_interventions`).
2. Pour chaque intervention dans cet ordre, tester toutes les dates de début `t ∈ [1, tmax_i]`
   et garder celle qui augmente le moins le coût (risque + pénalité de violation).
3. Le résultat sert de solution initiale à la métaheuristique.

## Fonctions utiles déjà présentes dans `src/`

| Fonction | Fichier | Rôle dans le glouton |
|---|---|---|
| `read_instance(path)` | `reader.py` | charge l'instance JSON (dict brut) |
| `start_candidates(intervention, horizon)` | `reader.py` | dates de début possibles `1 .. min(tmax, T)` → boucle sur les `t` à tester |
| `duration(intervention, start)` | `reader.py` | durée si début en `start` → périodes occupées `[start, start + durée[` |
| `sort_interventions(instance, a, b, c)` | `indicateurs.py` | ordre de placement (plus difficile d'abord) |
| `compute_indicators(instance)` | `indicateurs.py` | indicateurs bruts (`R_min` donne aussi la meilleure date « seule ») |
| `difficulty_scores(indicators, a, b, c)` | `indicateurs.py` | score de difficulté, pour tester d'autres poids sans recalculer les indicateurs |
| `write_solution(path, starts)` | `writer.py` | écrit `{nom: date}` au format attendu par le checker |
| `Evaluation(instance, lam)` | `evaluation.py` | état de la solution + coût incrémental (voir ci-dessous) |

Validation (hors `src/`, dans `RTE_ChallengeROADEF2020_checker.py`) :
`python3 RTE_ChallengeROADEF2020_checker.py <instance.json> <solution.txt>`.
Ses fonctions (`compute_resources`, `compute_objective`, `check_all_constraints`) affichent beaucoup
et modifient l'instance (clé `start`) : à utiliser pour vérifier une solution finale, pas dans la boucle du glouton.

Coût incrémental : `src/evaluation.py`. Dans le glouton :
`ev.delta({i: t})` pour chaque date candidate `t`, puis `ev.assign({i: meilleure_date})`.

## Indicateurs par intervention (`compute_indicators`)

| Indicateur | Définition |
|---|---|
| `F` | flexibilité : nombre de dates de début possibles |
| `D` | durée moyenne sur les dates possibles |
| `W` | charge relative moyenne par période : somme sur les ressources de `workload / max` |
| `R_min`, `R_max`, `R_moy` | risque moyen (sur les scénarios) cumulé sur la durée, selon la date de début |
| `Reg` | regret : `R(2e meilleure date) − R(meilleure date)` |
| `sigma` | écart-type moyen du risque entre scénarios (lié au terme d'excès / quantile) |
| `E` | nombre d'exclusions impliquant l'intervention |

## Score de difficulté (`difficulty_scores`)

```
score = a·tension + b·exclusion + c·regret     (chaque terme normalisé dans [0, 1])

tension   = W·D / F      lourde, longue et peu flexible
exclusion = E / F        beaucoup d'incompatibilités pour peu de choix
regret    = Reg / R_moy  perd beaucoup si elle rate son meilleur créneau
```

Poids par défaut : `a=1, b=1, c=0.5` (la faisabilité passe avant le regret).

## Points d'attention

- **Ressources min** : impossibles à garantir pendant la construction → pénalité ou réparation en fin de glouton.
- **Objectif non séparable** (quantile) : garder le risque par période et par scénario en mémoire
  et calculer le coût marginal de façon incrémentale.
- **Blocage** (aucune date réalisable) : version randomisée (GRASP, choix parmi les k meilleurs) + relances.
- `sigma` vaut 0 sur les instances à un seul scénario (ex. A_01).

## Format d'instance (vérifié sur A_01 et B_01)

- `tmax` est une chaîne, `Delta` contient des flottants → convertir en `int`.
- `workload[c][t][start]` est creux : clé absente = 0.
- `risk[t][start]` = liste d'une valeur par scénario ; `Scenarios_number[t]` varie selon `t`.
- Instances B dans `B_set/B_set_rounded/`.

## À faire

- [ ] Coder le glouton dans `src/heuristique.py` à partir de `sort_interventions`.
- [ ] Régler les poids `a`, `b`, `c` par type d'instance.
