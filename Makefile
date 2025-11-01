
DATA_DIR := $(HOME)/Smartwatch
TOOLS_DIR := ./tools

LINT_FILES := *.py

lint:
	@pylint $(LINT_FILES)
	@flake8 $(LINT_FILES)

.PHONY: sync
sync:
	@$(TOOLS_DIR)/sync.sh

.PHONY: steps
steps:
	# <Garmin>/Monitor/*: Forerunner saves steps state in the files there
	# Normally once a day, however there are intermediate states
	@./fitparse.py -c steps -p $(DATA_DIR)/Monitor/*
