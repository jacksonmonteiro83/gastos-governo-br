.PHONY: ingest build test inspecionar

ingest:
	python -m pipeline.bcb
	python -m pipeline.tesouro

inspecionar:
	python -m pipeline.tesouro --inspecionar

build:
	cd dbt && dbt build --profiles-dir .

test:
	python -m pytest -q
