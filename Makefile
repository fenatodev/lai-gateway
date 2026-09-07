PYTHON ?= python3
HARNESS_REPO ?= ../lai-local-agent
TARGET_GATEWAY ?= 0.1.34
MIN_HARNESS ?= 0.4.6
TARGET_HARNESS ?=

.PHONY: help test check milestone-gate smoke

help:
	@printf '%s\n' \
	  'lai-gateway development commands:' \
	  '  make test            Run dependency-free unittest suite' \
	  '  make check           Compile sources, scan publication surfaces, run tests, check static JS, and check metadata' \
	  '  make milestone-gate  Run check plus local Gateway/Harness stack compatibility gate' \
	  '  make smoke           Print local CLI help without contacting the harness'

test:
	python3 -m unittest discover -s tests -t . -v

check:
	$(PYTHON) -m compileall -q lai_gateway tests
	$(PYTHON) -m py_compile lai_gateway/*.py tests/*.py
	bash -n scripts/*.sh
	bash scripts/publication-scan.sh
	@if command -v node >/dev/null 2>&1; then node --check lai_gateway/static/app.js; else echo 'node not found; skipping JS syntax check'; fi
	$(PYTHON) -m unittest discover -s tests -t . -v
	$(PYTHON) -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
	git diff --check

milestone-gate: check
	PYTHON="$(PYTHON)" bash scripts/stack-check.sh --harness-repo "$(HARNESS_REPO)" --target-gateway "$(TARGET_GATEWAY)" --min-harness "$(MIN_HARNESS)" $(if $(TARGET_HARNESS),--target-harness "$(TARGET_HARNESS)",) --json | $(PYTHON) -c 'import json, sys; payload = json.load(sys.stdin); assert payload["overall"] == "ready_for_local_commit", payload; print("lai-gateway milestone-gate: ready_for_local_commit")'

smoke:
	$(PYTHON) -m lai_gateway --help >/dev/null
