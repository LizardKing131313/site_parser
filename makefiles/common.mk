# ---- OS-aware venv layout ----------------------------------------------------
ifeq ($(OS),Windows_NT)
VENV_BIN := .venv/Scripts
PY       := python
NULLDEV  := NUL
else
VENV_BIN := .venv/bin
PY       := python3
NULLDEV  := /dev/null
endif

PIP      := $(VENV_BIN)/pip
PYTHON   := $(VENV_BIN)/python

# Tools inside venv (не вызываем activate)
PIP_COMPILE := $(VENV_BIN)/pip-compile
PIP_SYNC    := $(VENV_BIN)/pip-sync

# Проектные пути/утилиты
RUFF     := $(VENV_BIN)/ruff
BLACK    := $(VENV_BIN)/black
MYPY     := $(VENV_BIN)/mypy
PYTEST   := $(VENV_BIN)/pytest
