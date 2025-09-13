# ---- Helpers -----------------------------------------------------------------
.PHONY: help-dev
help-dev:
	@echo "Targets:"
	@echo "  lint 					 - check code files with configuration from pyproject.toml"
	@echo "  format  				 - check and auto fix code files with configuration from pyproject.toml"
	@echo "  typecheck  		 - mypy type checks with configuration from pyproject.toml"
	@echo "  test  					 - run pytest. Stop after first failed test"
	@echo "  test-all  			 - run all pytest"
	@echo "  coverage  			 - run all pytest with coverage"
	@echo "  coverage-badge  - generate coverage badge"
	@echo "  ci  						 - run linter and tests"

# ---- DEV ---------------------------------------------------------------------
.PHONY: lint
lint:
	$(RUFF) check .
	$(BLACK) --check .

.PHONY: format
format:
	$(RUFF) check . --fix
	$(BLACK) .

.PHONY: typecheck
typecheck:
	$(MYPY) "--config-file=pyproject.toml"

.PHONY: test
test:
	$(PYTEST) --maxfail=1 -q --disable-warnings

.PHONY: test-all
test-all:
	$(PYTEST) -q --disable-warnings

.PHONY: coverage
coverage:
	$(PYTEST) -q --disable-warnings --cov=. --cov-report=term-missing --cov-report=xml --cov-report=html

.PHONY: coverage-badge
coverage-badge:
	$(PYTHON) scripts/badge/gen_badge.py

.PHONY: ci
ci: lint test
