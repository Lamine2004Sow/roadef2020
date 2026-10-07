# Usage :
#   make install
#   make heuristique     INSTANCE=A_set/A_01.json
#   make metaheuristique INSTANCE=A_set/A_01.json
#   make check INSTANCE=A_set/A_01.json [SOLUTION=solutions/A_01.txt]
#   make clean

PYTHON   ?= python3
INSTANCE ?= A_set/A_01.json
OUT      ?= solutions
NAME      = $(basename $(notdir $(INSTANCE)))
SOLUTION ?= $(OUT)/$(NAME).txt

.PHONY: help install heuristique metaheuristique check clean

help:
	@echo "make install                              installe les dépendances"
	@echo "make heuristique     INSTANCE=...         glouton    -> $(OUT)/<instance>_heuristique.txt + checker"
	@echo "make metaheuristique INSTANCE=...         recuit     -> $(OUT)/<instance>_metaheuristique.txt + checker"
	@echo "make check INSTANCE=... [SOLUTION=...]    vérifie une solution avec le checker officiel"
	@echo "make clean                                supprime les caches Python"

install:
	$(PYTHON) -m pip install -r requirements.txt

heuristique:
	@mkdir -p $(OUT)
	$(PYTHON) src/heuristique.py $(INSTANCE) $(OUT)/$(NAME)_heuristique.txt
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(OUT)/$(NAME)_heuristique.txt

metaheuristique:
	@mkdir -p $(OUT)
	$(PYTHON) src/meta_heuristique.py $(INSTANCE) $(OUT)/$(NAME)_metaheuristique.txt
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(OUT)/$(NAME)_metaheuristique.txt

check:
	$(PYTHON) RTE_ChallengeROADEF2020_checker.py $(INSTANCE) $(SOLUTION)

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
