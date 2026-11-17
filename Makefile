.PHONY: ingest build build-cpgf conferir test inspecionar

ingest:
	python -m pipeline.bcb
	python -m pipeline.tesouro

inspecionar:
	python -m pipeline.tesouro --inspecionar

build:   # tudo menos o CPGF (o Parquet do cartão só existe no workflow do CPGF)
	cd dbt && dbt build --exclude tag:cpgf --profiles-dir .

build-cpgf:
	cd dbt && dbt build --select +tag:cpgf --profiles-dir .

conferir:
	python -m pipeline.conferir_dbt

test:
	python -m pytest -q
