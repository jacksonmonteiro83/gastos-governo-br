from pipeline.conferir_dbt import comparar_rgps

PAINEL = {"anos": [2023, 2024], "arrecadacao": [100.0, 110.0], "beneficios": [150.0, 170.0], "necessidade": [50.0, 60.0]}


def test_bate():
    assert comparar_rgps([(2023, 100.04, 150.0, 49.96), (2024, 110.0, 170.0, 60.0)], PAINEL) == []


def test_diverge_e_ano_ausente():
    erros = comparar_rgps([(2024, 110.0, 171.0, 61.0), (2025, 1.0, 1.0, 0.0)], PAINEL)
    assert any("2024 beneficios" in e for e in erros) and any("2025" in e for e in erros)


from pipeline.conferir_dbt import comparar_despesas

DESP = {"anos": [2024, 2025], "total_bi": [3000.0, 3269.1],
        "composicao": {"Previdência social": [30.0, 32.8], "Outras": [70.0, 67.2]}}


def test_despesas_bate():
    assert comparar_despesas([(2025, 3269.1)], [(2025, "Previdência social", 32.84)], DESP) == []


def test_despesas_diverge_e_ausente():
    erros = comparar_despesas([(2025, 3300.0), (2026, 1.0)], [(2025, "Outras", 60.0), (2025, "Inexistente", 1.0)], DESP)
    assert any("2025 total" in e for e in erros)
    assert any("2026" in e for e in erros)
    assert any("2025 Outras" in e for e in erros)
    assert any("Inexistente" in e for e in erros)


from pipeline.conferir_dbt import comparar_emendas

EMD = {"anos": [2024, 2025], "total_bi": [41.0, 49.7], "executado_pct": [90.0, None],
       "tipos": {"Bancada": [10.0, 12.0], "Relator": [0.0, 0.0]}}


def test_emendas_bate():
    assert comparar_emendas([(2025, 49.7, None), (2024, 41.04, 90.0)], [(2025, "Bancada", 12.05)], EMD) == []


def test_emendas_diverge():
    erros = comparar_emendas([(2025, 55.0, 80.0), (2026, 1.0, 1.0)], [(2025, "Bancada", 9.0), (2025, "Outro", 1.0)], EMD)
    assert any("2025 total" in e for e in erros) and any("2025 executado" in e for e in erros)
    assert any("2026" in e for e in erros) and any("2025 Bancada" in e for e in erros) and any("Outro" in e for e in erros)
