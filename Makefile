.PHONY: all data train eval demo test lint clean

PYTHON ?= python

all: data train eval test

data:
	$(PYTHON) -m sim.generate_world

train:
	$(PYTHON) -m eta.train
	$(PYTHON) -m demand.train

eval:
	$(PYTHON) -m eval.run_eval

demo:
	$(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -c "import core.schemas, api.main; print('Syntax and imports OK')"

clean:
	-rm -rf __pycache__ .pytest_cache data/raw data/processed results/*.png
