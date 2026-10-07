"""Lecture d'une instance JSON ROADEF 2020."""
import json


def read_instance(path: str) -> dict:
    """Charge l'instance et retourne le dict brut (clés : T, Resources, Interventions, ...)."""
    with open(path, 'r') as f:
        return json.load(f)


def start_candidates(intervention: dict, horizon: int) -> range:
    """Dates de début possibles d'une intervention : 1 .. min(tmax, T)."""
    return range(1, min(int(intervention['tmax']), horizon) + 1)


def duration(intervention: dict, start: int) -> int:
    """Durée de l'intervention si elle commence au jour `start`."""
    return int(intervention['Delta'][start - 1])
