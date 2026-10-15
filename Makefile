test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
run:
	PYTHONPATH=src python3 -m leanbridge run --scenario abrupt_drop --seed 1 --out runs/demo
.PHONY: test run
