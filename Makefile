# Headless development and release commands for model-agrologistic.

PYTHON ?= python3.13
TRL6_OUTPUT ?= data/results/releases/trl6-v0.1.0-candidate

.PHONY: help install lint test audit protocol-plan preflight protocol evidence build

help:
	@echo "make install       Install the project and development requirements"
	@echo "make lint          Run Ruff"
	@echo "make test          Run the complete test suite"
	@echo "make audit         Audit repository hygiene"
	@echo "make protocol-plan Print the ordered TRL 6 protocol"
	@echo "make preflight     Run quality, data, and model-size preflight checks"
	@echo "make protocol      Run the complete licensed TRL 6 protocol"
	@echo "make evidence      Rebuild evidence from the configured accepted runs"
	@echo "make build         Build source and wheel distributions"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

audit:
	$(PYTHON) scripts/audit_repository_hygiene.py

protocol-plan:
	$(PYTHON) scripts/run_trl6_protocol.py --print-plan --output-dir $(TRL6_OUTPUT)

preflight:
	$(PYTHON) scripts/run_trl6_protocol.py --fetch-artur-assets --output-dir $(TRL6_OUTPUT)

protocol:
	$(PYTHON) scripts/run_trl6_protocol.py --fetch-artur-assets --execute-solver --output-dir $(TRL6_OUTPUT)

evidence:
	$(PYTHON) scripts/build_mvp_scientific_evidence.py

build:
	$(PYTHON) -m build
