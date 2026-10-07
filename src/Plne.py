"""PLNE avec Gurobi. Usage : python src/Plne.py <instance.json> <solution.txt>"""
import sys

try:
    import gurobipy as gp
except ImportError:
    gp = None

# Au-delà de cette taille, la licence gratuite fournie avec `pip install gurobipy` refuse le modèle
RESTRICTED_LIMIT = 2000


def gurobi_env():
    """Retourne un environnement Gurobi, ou arrête le programme avec un message clair
    si gurobipy est absent, sans licence, ou avec la licence restreinte de pip."""
    if gp is None:
        sys.exit("PLNE indisponible : gurobipy n'est pas installé (lancer `make install`).")
    try:
        env = gp.Env(empty=True)
        env.setParam('OutputFlag', 0)
        env.start()
        # Test de taille : échoue avec l'erreur SIZE_LIMIT_EXCEEDED si la licence est restreinte
        with gp.Model(env=env) as m:
            m.addVars(RESTRICTED_LIMIT + 1)
            m.optimize()
    except gp.GurobiError as e:
        if e.errno == gp.GRB.Error.SIZE_LIMIT_EXCEEDED:
            sys.exit('PLNE indisponible : licence Gurobi restreinte (limitée à 2000 variables). '
                     'Une licence complète (académique gratuite) est requise.')
        sys.exit(f'PLNE indisponible : licence Gurobi introuvable ou invalide '
                 f'(vérifier GRB_LICENSE_FILE). Détail : {e}')
    return env


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage : python src/Plne.py <instance.json> <solution.txt>')
    gurobi_env()
    sys.exit('PLNE : modèle pas encore implémenté.')


if __name__ == '__main__':
    main()
