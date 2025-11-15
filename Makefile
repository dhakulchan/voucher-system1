PY?=python

.PHONY: run test benchmark precommit-install pdf-benchmark multiscript-check

run:
	$(PY) run.py

test:
	$(PY) -m pytest -q

benchmark:
	$(PY) scripts/pdf_benchmark.py --runs 3 --quiet

pdf-benchmark: benchmark

precommit-install:
	$(PY) -m pip install pre-commit && pre-commit install

multiscript-check:
	$(PY) -m pytest -q test_multiscript_fonts.py
