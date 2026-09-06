.PHONY: help test check smoke

help:
	@printf '%s\n' \
	  'lai-gateway development commands:' \
	  '  make test   Run dependency-free unittest suite' \
	  '  make check  Compile sources, run tests, and check basic packaging metadata' \
	  '  make smoke  Print local CLI help without contacting the harness'

test:
	python3 -m unittest discover -s tests -t . -v

check:
	python3 -m compileall -q lai_gateway tests
	python3 -m py_compile lai_gateway/*.py tests/*.py
	python3 -m unittest discover -s tests -t . -v
	python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"
	git diff --check

smoke:
	python3 -m lai_gateway --help >/dev/null
