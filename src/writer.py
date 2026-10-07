"""Écriture d'une solution au format texte : une ligne `nom_intervention date_début`."""


def write_solution(path: str, starts: dict) -> None:
    with open(path, 'w') as f:
        for name, start in starts.items():
            f.write(f'{name} {start}\n')
