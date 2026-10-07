# Usage :
#   make install
#   make heuristique     INSTANCE=A_set/A_01.json
#   make metaheuristique INSTANCE=A_set/A_01.json
#   make plne            INSTANCE=A_set/A_01.json   (Gurobi requis)
#   make graphes [INSTANCE=... SOLUTION=...]
#   make check INSTANCE=A_set/A_01.json [SOLUTION=solutions/A_01.txt]
#   make clean

VENV     ?= .venv
# Python du .venv s'il existe, sinon celui du système
PYTHON   ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
INSTANCE ?= A_set/A_01.json
OUT      ?= solutions
NAME      = $(basename $(notdir $(INSTANCE)))
SOLUTION ?= $(OUT)/$(NAME).txt

.PHONY: help install heuristique metaheuristique plne graphes check clean

help:
	@echo "make install                              crée $(VENV) et y installe requirements.txt"
	@echo "make heuristique     INSTANCE=...         glouton    -> $(OUT)/<instance>_heuristique.txt + checker"
	@echo "make metaheuristique INSTANCE=...         recuit     -> $(OUT)/<instance>_metaheuristique.txt + checker"
	@echo "make plne            INSTANCE=...         PLNE Gurobi -> $(OUT)/<instance>_plne.txt + checker"
	@echo "make graphes [INSTANCE=... SOLUTION=...] graphes du rapport -> results/figures/"
	@echo "make check INSTANCE=... [SOLUTION=...]    vérifie une solution avec le checker officiel"
	@echo "make clean                                supprime les caches Python"

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -r requirements.txt

heuristique:
	@mkdir -p $(OUT)
	$(PYTHON) src/heuristique.py $(INSTANCE) $(OUT)/$(NAME)_heuristique.txt
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(OUT)/$(NAME)_heuristique.txt

metaheuristique:
	@mkdir -p $(OUT)
	$(PYTHON) src/meta_heuristique.py $(INSTANCE) $(OUT)/$(NAME)_metaheuristique.txt
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(OUT)/$(NAME)_metaheuristique.txt

plne:
	@mkdir -p $(OUT)
	$(PYTHON) src/Plne.py $(INSTANCE) $(OUT)/$(NAME)_plne.txt
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(OUT)/$(NAME)_plne.txt

# Graphes 1 à 8 depuis results/ ; 9 à 11 en plus si SOLUTION existe
graphes:
	$(PYTHON) src/graphes.py $(if $(wildcard $(SOLUTION)),$(INSTANCE) $(SOLUTION))

check:
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(SOLUTION)

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
