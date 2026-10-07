"""Indicateurs par intervention pour trier le glouton (de la plus difficile à la plus facile)."""
import numpy as np

from reader import start_candidates, duration


def compute_indicators(instance: dict) -> dict:
    """Retourne {nom: {F, D, W, R_min, R_max, R_moy, Reg, sigma, E}} pour chaque intervention.

    F     : flexibilité = nombre de dates de début possibles
    D     : durée moyenne sur les dates de début possibles
    W     : charge relative moyenne par période (somme sur les ressources de workload / max)
    R_*   : risque moyen (sur les scénarios) cumulé sur la durée, selon la date de début
    Reg   : regret = R(2e meilleure date) - R(meilleure date)
    sigma : écart-type moyen du risque entre scénarios (influence l'excès / quantile)
    E     : nombre d'exclusions impliquant l'intervention
    """
    T = instance['T']
    resources = instance['Resources']
    scen = instance['Scenarios_number']

    nb_excl = {name: 0 for name in instance['Interventions']}
    for i1, i2, _season in instance['Exclusions'].values():
        nb_excl[i1] += 1
        nb_excl[i2] += 1

    indicators = {}
    for name, interv in instance['Interventions'].items():
        starts = start_candidates(interv, T)
        durations, risks, sigmas, charges = [], [], [], []
        for s in starts:
            d = duration(interv, s)
            periods = range(s, min(s + d, T + 1))
            # Risque moyen et dispersion entre scénarios sur la durée de l'intervention
            r, sig = 0.0, 0.0
            for t in periods:
                values = interv['risk'][str(t)][str(s)]
                r += sum(values) / scen[t - 1]
                sig += float(np.std(values))
            # Charge relative : workload absent = 0, max nul ignoré
            w = 0.0
            for res_name, wl in interv['workload'].items():
                cap = resources[res_name]['max']
                for t in periods:
                    val = wl.get(str(t), {}).get(str(s), 0.0)
                    if val and cap[t - 1] > 0:
                        w += val / cap[t - 1]
            durations.append(d)
            risks.append(r)
            sigmas.append(sig / max(d, 1))
            charges.append(w / max(d, 1))

        sorted_risks = sorted(risks)
        indicators[name] = {
            'F': len(starts),
            'D': float(np.mean(durations)),
            'W': float(np.mean(charges)),
            'R_min': sorted_risks[0],
            'R_max': sorted_risks[-1],
            'R_moy': float(np.mean(risks)),
            'Reg': sorted_risks[1] - sorted_risks[0] if len(sorted_risks) > 1 else 0.0,
            'sigma': float(np.mean(sigmas)),
            'E': nb_excl[name],
        }
    return indicators


def _normalize(values: dict) -> dict:
    """Ramène les valeurs dans [0, 1] (division par le max)."""
    m = max(values.values(), default=0.0)
    return {k: (v / m if m > 0 else 0.0) for k, v in values.items()}


def difficulty_scores(indicators: dict, a: float = 1.0, b: float = 1.0, c: float = 0.5) -> dict:
    """score = a·tension + b·exclusion + c·regret, chaque terme normalisé dans [0, 1].

    tension   = W·D / F   (lourde, longue et peu flexible)
    exclusion = E / F     (beaucoup d'incompatibilités pour peu de choix)
    regret    = Reg / R_moy
    """
    tension = _normalize({n: x['W'] * x['D'] / x['F'] for n, x in indicators.items()})
    exclusion = _normalize({n: x['E'] / x['F'] for n, x in indicators.items()})
    regret = _normalize({n: (x['Reg'] / x['R_moy'] if x['R_moy'] > 0 else 0.0)
                         for n, x in indicators.items()})
    return {n: a * tension[n] + b * exclusion[n] + c * regret[n] for n in indicators}


def sort_interventions(instance: dict, a: float = 1.0, b: float = 1.0, c: float = 0.5) -> list:
    """Ordre du glouton : score décroissant (les plus difficiles d'abord)."""
    scores = difficulty_scores(compute_indicators(instance), a, b, c)
    return sorted(scores, key=scores.get, reverse=True)
