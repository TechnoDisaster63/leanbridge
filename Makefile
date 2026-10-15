PYTHON ?= python3
export PYTHONPATH := src

.PHONY: help test check run screen

help:
	@printf '%s\n' 'make check  - tests, syntax and local documentation links' 'make test   - unit and regression tests' 'make run    - one offline simulated demo in runs/demo' 'make screen - toy screening, not confirmatory research'

test:
	$(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) check.py

run:
	$(PYTHON) -m leanbridge run --scenario abrupt_drop --seed 1 --out runs/demo

screen:
	$(PYTHON) -m leanbridge bench --seeds 10
