# PLNE (Gurobi)

Fichier : `src/Plne.py`

## Dépendance à Gurobi

- Seule méthode du projet qui utilise Gurobi ; glouton et recuit n'en dépendent pas.
- **Pas de solveur alternatif** (PuLP + HiGHS/CBC écarté) : sans Gurobi, les solveurs libres
  ne résoudraient que les petites instances A, pour beaucoup de code en plus.
- `gurobi_env()` arrête proprement le programme avec un message clair si :
  - `gurobipy` n'est pas installé ;
  - la licence est introuvable ou invalide (`GRB_LICENSE_FILE`) ;
  - la licence est la licence restreinte de pip (> 2000 variables refusées), détectée par un
    modèle test de 2001 variables (erreur `SIZE_LIMIT_EXCEEDED`).
- Licence actuelle : académique, valable jusqu'au 2027-09-02.

## À faire

- [ ] Modèle : variables de date de début, ressources, exclusions, linéarisation du quantile.
