#!/usr/bin/env bash
# Usage : ./run.sh <instance.json> [solution.txt]
# Résout l'instance puis vérifie la solution avec le checker officiel.
set -e
INSTANCE="$1"
SOLUTION="${2:-solutions/$(basename "${INSTANCE%.json}").txt}"
python3 src/main.py "$INSTANCE" "$SOLUTION"
python3 RTE_ChallengeROADEF2020_checker.py "$INSTANCE" "$SOLUTION"
