
DATA_DIR := $(HOME)/Smartwatch
TOOLS_DIR := ./tools

LINT_FILES := *.py

lint:
	@pylint $(LINT_FILES)
	@flake8 $(LINT_FILES)

.PHONY: test
test: lint
	@./tests/all_test.sh
	@./tests/fit2sqlite.sh

.PHONY: sync
sync:
	@$(TOOLS_DIR)/sync.sh

.PHONY: steps
steps:
	# <Garmin>/Monitor/*: Forerunner saves steps state in the files there
	# Normally once a day, however there are intermediate states
	@./fitparse.py -c steps -p $(DATA_DIR)/Monitor/*

.PHONY: sync-db
sync-db:
	./tools/db_files_to_update.sh | ./fit2sqlite.py -b
