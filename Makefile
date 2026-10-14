.PHONY: all data train eval demo test lint clean

# Default to conda environment python if on Windows, else standard python
ifeq ($(OS),Windows_NT)
  CONDA_PY := $(wildcard C:/Users/Lenovo/miniconda3/envs/tracknet/python.exe)
  ifneq ($(CONDA_PY),)
    PYTHON ?= $(CONDA_PY)
  else
    PYTHON ?= python
  endif
else
  PYTHON ?= python
endif

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
