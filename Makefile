
VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

setup:
	python -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt

fetch:
	$(PY) pipeline/fetch_fpl_data.py all

xgxa:
	$(PY) pipeline/ingest_xgxa.py --season 2024

project:
	$(PY) pipeline/compute_phase3.py --next_n 5

app:
	streamlit run app/app.py
