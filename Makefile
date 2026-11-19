.PHONY: ingest build build-cpgf build-despesas build-emendas conferir conferir-despesas conferir-emendas test inspecionar

ingest:
	python -m pipeline.bcb
	python -m pipeline.tesouro

inspecionar:
	python -m pipeline.tesouro --inspecionar

build:   # tudo menos o CPGF (o Parquet do cartão só existe no workflow do CPGF)
	cd dbt && dbt build --exclude tag:cpgf tag:despesas tag:emendas --profiles-dir .

build-cpgf:
	cd dbt && dbt build --select +tag:cpgf --profiles-dir .

build-despesas:   # o Parquet do orçamento só existe no workflow das despesas
	cd dbt && dbt build --select +tag:despesas --profiles-dir .

build-emendas:    # o Parquet das emendas só existe no workflow das emendas
	cd dbt && dbt build --select +tag:emendas --profiles-dir .

conferir:
	python -m pipeline.conferir_dbt

conferir-despesas:
	python -m pipeline.conferir_dbt --despesas

conferir-emendas:
	python -m pipeline.conferir_dbt --emendas

test:
	python -m pytest -q
