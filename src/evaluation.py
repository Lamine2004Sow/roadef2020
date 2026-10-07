"""Évaluation incrémentale d'une solution : objectif ROADEF + pénalité des contraintes violées.

coût = objectif + λ · (violations ressources + violations exclusions)

objectif = (1/T) · Σ_t [ α · moyenne_t + (1 − α) · max(quantile_t − moyenne_t, 0) ]
           (même calcul que RTE_ChallengeROADEF2020_checker.py)

Un changement (déplacement, swap, ajout, retrait) ne recalcule que les périodes
occupées par les interventions concernées, avant et après le changement.
"""
import numpy as np

from reader import duration


class Evaluation:

    def __init__(self, instance: dict, lam: float = 1.0):
        self.T = instance['T']
        self.alpha = instance['Alpha']
        self.lam = lam
        self.interventions = instance['Interventions']
        scen = instance['Scenarios_number']
        # Indice du quantile dans la liste triée des scénarios (comme le checker)
        self.q_idx = [int(np.ceil(n * instance['Quantile'])) - 1 for n in scen]

        resources = instance['Resources']
        self.res_index = {c: k for k, c in enumerate(resources)}
        self.r_min = np.array([resources[c]['min'] for c in resources], dtype=float)
        self.r_max = np.array([resources[c]['max'] for c in resources], dtype=float)

        # Saisons : somme cumulée pour compter en O(1) les périodes d'une saison dans [a, b]
        self.season_prefix = {}
        for season, periods in instance['Seasons'].items():
            mask = np.zeros(self.T + 1, dtype=int)
            for t in periods:
                mask[int(t)] = 1
            self.season_prefix[season] = np.cumsum(mask)
        self.excl = {name: [] for name in self.interventions}
        for i1, i2, season in instance['Exclusions'].values():
            self.excl[i1].append((i2, season))
            self.excl[i2].append((i1, season))

        # État courant
        self.start = {}
        self.risk = [np.zeros(n) for n in scen]
        self.usage = np.zeros((len(resources), self.T))
        self.period_cost = np.zeros(self.T)
        self.res_viol = np.maximum(self.r_min - self.usage, 0.0)
        self.excl_viol = 0
        self._cache = {}

    # ------------------------------------------------------------------ données

    def can_start(self, i: str, s: int) -> bool:
        return 1 <= s <= min(int(self.interventions[i]['tmax']), self.T)

    def _data(self, i: str, s: int):
        """(première période, fin exclue, risques par période, charges) en indices 0, mis en cache."""
        key = (i, s)
        if key not in self._cache:
            interv = self.interventions[i]
            first = s - 1
            end = min(first + duration(interv, s), self.T)
            risks = [np.asarray(interv['risk'][str(t + 1)][str(s)], dtype=float)
                     for t in range(first, end)]
            ks, ts, vals = [], [], []
            for c, wl in interv['workload'].items():
                for t in range(first, end):
                    val = wl.get(str(t + 1), {}).get(str(s))
                    if val:
                        ks.append(self.res_index[c])
                        ts.append(t)
                        vals.append(val)
            self._cache[key] = (first, end, risks,
                                (np.array(ks, dtype=int), np.array(ts, dtype=int)),
                                np.array(vals, dtype=float))
        return self._cache[key]

    def _apply(self, i: str, s: int, sign: int):
        first, _end, risks, idx, vals = self._data(i, s)
        for k, r in enumerate(risks):
            self.risk[first + k] += sign * r
        np.add.at(self.usage, idx, sign * vals)

    def _refresh(self, periods: np.ndarray):
        """Recalcule coût par période et violations ressources sur `periods`."""
        for t in periods:
            r = self.risk[t]
            mean = r.mean()
            q = np.partition(r, self.q_idx[t])[self.q_idx[t]]
            self.period_cost[t] = self.alpha * mean + (1 - self.alpha) * max(q - mean, 0.0)
        u = self.usage[:, periods]
        self.res_viol[:, periods] = (np.maximum(u - self.r_max[:, periods], 0.0)
                                     + np.maximum(self.r_min[:, periods] - u, 0.0))

    def _overlap(self, i: str, j: str, season: str) -> int:
        """Nombre de périodes de `season` où i et j sont simultanément en cours."""
        if i not in self.start or j not in self.start:
            return 0
        fi, ei = self._data(i, self.start[i])[:2]
        fj, ej = self._data(j, self.start[j])[:2]
        a, b = max(fi, fj) + 1, min(ei, ej)  # périodes 1-indexées [a, b]
        if a > b:
            return 0
        prefix = self.season_prefix[season]
        return int(prefix[b] - prefix[a - 1])

    # ------------------------------------------------------------- changements

    def assign(self, changes: dict) -> float:
        """Applique {intervention: date ou None (retrait)} et retourne la variation du coût.

        Pour annuler : `self.assign(old)` avec `old = {i: self.start.get(i) for i in changes}`.
        """
        periods, pairs = set(), set()
        for i, s in changes.items():
            for s2 in (self.start.get(i), s):
                if s2 is not None:
                    first, end = self._data(i, s2)[:2]
                    periods.update(range(first, end))
            for j, season in self.excl[i]:
                pairs.add((min(i, j), max(i, j), season))
        periods = np.fromiter(sorted(periods), dtype=int)

        before_excl = sum(self._overlap(a, b, s) for a, b, s in pairs)
        before = self.period_cost[periods].sum() / self.T + self.lam * self.res_viol[:, periods].sum()

        for i in changes:
            if i in self.start:
                self._apply(i, self.start.pop(i), -1)
        for i, s in changes.items():
            if s is not None:
                self._apply(i, s, +1)
                self.start[i] = s
        self._refresh(periods)

        after_excl = sum(self._overlap(a, b, s) for a, b, s in pairs)
        after = self.period_cost[periods].sum() / self.T + self.lam * self.res_viol[:, periods].sum()
        self.excl_viol += after_excl - before_excl
        return after - before + self.lam * (after_excl - before_excl)

    def delta(self, changes: dict) -> float:
        """Variation du coût si on appliquait `changes`, sans modifier l'état."""
        old = {i: self.start.get(i) for i in changes}
        d = self.assign(changes)
        self.assign(old)
        return d

    def swap_changes(self, i: str, j: str):
        """Changements d'un swap des dates de i et j, ou None si une date sort de [1, tmax]."""
        si, sj = self.start[i], self.start[j]
        if not (self.can_start(i, sj) and self.can_start(j, si)):
            return None
        return {i: sj, j: si}

    # ----------------------------------------------------------------- lecture

    def interventions_en_violation(self, tol: float = 1e-5) -> list:
        """Interventions en cours sur une période où une ressource est violée,
        ou impliquées dans une exclusion violée."""
        bad = self.res_viol.sum(axis=0) > tol
        result = []
        for i, s in self.start.items():
            first, end = self._data(i, s)[:2]
            if bad[first:end].any() or any(self._overlap(i, j, season) > 0 for j, season in self.excl[i]):
                result.append(i)
        return result

    def objective(self) -> float:
        return self.period_cost.sum() / self.T

    def violation(self) -> float:
        return self.res_viol.sum() + self.excl_viol

    def cost(self) -> float:
        return self.objective() + self.lam * self.violation()

    def set_lambda(self, lam: float):
        self.lam = lam
