from pipeline.conferir_dbt import comparar_rgps

PAINEL = {"anos": [2023, 2024], "arrecadacao": [100.0, 110.0], "beneficios": [150.0, 170.0], "necessidade": [50.0, 60.0]}


def test_bate():
    assert comparar_rgps([(2023, 100.04, 150.0, 49.96), (2024, 110.0, 170.0, 60.0)], PAINEL) == []


def test_diverge_e_ano_ausente():
    erros = comparar_rgps([(2024, 110.0, 171.0, 61.0), (2025, 1.0, 1.0, 0.0)], PAINEL)
    assert any("2024 beneficios" in e for e in erros) and any("2025" in e for e in erros)
