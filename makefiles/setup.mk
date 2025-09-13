# ---- Helpers -----------------------------------------------------------------
.PHONY: help-setup
help-setup:
	@echo "Targets:"
	@echo "  venv            - create virtualenv (.venv)"
	@echo "  upgrade-pip     - upgrade pip/setuptools/wheel"
	@echo "  pip-tools       - install pip-tools (pip-compile, pip-sync)"
	@echo "  setup           - venv + upgrade + pip-tools + editable '.[dev]' + pre-commit install"
	@echo "  hooks           - reapply pre-commit hooks if config .pre-commit-config.yaml was changed"
	@echo "  compile         - compile requirements.txt"
	@echo "  compile-dev     - compile requirements-dev.txt"
	@echo "  compile-all     - compile requirements-all.txt"
	@echo "  compile-every   - compile all requirements files"
	@echo "  compile-update  - update all lock-files (set latest compatible versions)"
	@echo "  sync            - pip-sync env to requirements.txt"
	@echo "  sync-dev        - pip-sync env to requirements-dev.txt"
	@echo "  sync-all        - pip-sync env to requirements-all.txt"
	@echo "  clean-venv      - remove .venv"

# ---- Venv --------------------------------------------------------------------
.venv:  ## stamp-dir to mark venv
	$(PY) -m venv .venv
	@mkdir -p .venv 2>$(NULLDEV) || true
	@echo "ok" > .venv/.stamp

.PHONY: venv
venv: .venv

.PHONY: upgrade-pip
upgrade-pip: venv
	$(PYTHON) -m pip install -U pip setuptools wheel

# ---- pip-tools ---------------------------------------------------------------
.PHONY: pip-tools
pip-tools: upgrade-pip
	$(PIP) install -U pip-tools

# ---- Project setup -----------------------------------------------------------
.PHONY: setup
setup: venv upgrade-pip pip-tools
	# editable install if project uses pyproject/setuptools
	@if [ -f pyproject.toml ] || [ -f setup.cfg ] || [ -f setup.py ]; then \
		$(PIP) install -e ".[dev]" ; \
	else \
		echo "No build metadata found (pyproject.toml/setup.cfg); skipping editable install"; \
	fi
	# pre-commit
	$(PIP) install -U pre-commit
	$(MAKE) hooks

.PHONY: hooks
hooks:
	$(VENV_BIN)/pre-commit clean
	$(VENV_BIN)/pre-commit install

.PHONY: playwright
playwright: setup
	$(VENV_BIN)/playwright install chromium

# ---- Compile requirements ----------------------------------------------------
.PHONY: compile
compile: pip-tools
	$(PIP_COMPILE) pyproject.toml -o requirements.txt

.PHONY: compile-dev
compile-dev: pip-tools
	$(PIP_COMPILE) pyproject.toml --extra dev -o requirements-dev.txt

.PHONY: compile-all
compile-all: pip-tools
	$(PIP_COMPILE) pyproject.toml --extra dev --extra full -o requirements-all.txt

.PHONY: compile-every
compile-every: compile compile-dev compile-all

# ---- Compile requirements update ---------------------------------------------
.PHONY: compile-update
compile-update: compile-every
	$(PIP_COMPILE) -U pyproject.toml -o requirements.txt
	$(PIP_COMPILE) -U pyproject.toml --extra dev -o requirements-dev.txt
	$(PIP_COMPILE) -U pyproject.toml --extra dev --extra full -o requirements-all.txt

# ---- Sync (precise env) ------------------------------------------------------
.PHONY: sync
sync: pip-tools
	$(PIP_SYNC) requirements.txt

.PHONY: sync-dev
sync-dev: pip-tools
	$(PIP_SYNC) requirements-dev.txt

.PHONY: sync-all
sync-all: pip-tools
	$(PIP_SYNC) requirements-all.txt

# ---- Clean -------------------------------------------------------------------
.PHONY: clean-venv
clean-venv:
	@echo "Removing .venv ..."
ifeq ($(OS),Windows_NT)
	@if exist .venv rmdir /S /Q .venv
else
	@rm -rf .venv
endif
