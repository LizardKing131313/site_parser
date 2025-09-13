include makefiles/common.mk
include makefiles/setup.mk
include makefiles/dev.mk

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help-setup, help-dev"
	@echo "  venv, upgrade-pip, pip-tools, setup, hooks"
	@echo "  compile, compile-dev, compile-all, compile-every, compile-update"
	@echo "  sync, sync-dev, sync-all"
	@echo "  lint, format, typecheck, test, test-all, coverage, coverage-badge, ci"
