import pandas as pd

from pipeline.validar_juros import comparar, juros_tesouro


def _serie(valores, inicio="2024-01"):
    return pd.Series(valores, index=pd.period_range(inicio, periods=len(valores), freq="M"))


def test_juros_tesouro_inverte_sinal_e_usa_tabela_corrente():
    df = pd.DataFrame({
        "tabela": ["1.2", "1.2", "1.2-A"],
        "descricao": ["JUROS NOMINAIS", "JUROS NOMINAIS", "JUROS NOMINAIS"],
        "data": ["2024-01-01", "2024-02-01", "2024-01-01"],
        "valor": [-100.0, -200.0, -999.0],
    })
    s = juros_tesouro(df)
    assert s.tolist() == [100.0, 200.0]


def test_comparar_series_iguais():
    t = _serie([100.0] * 12)
    anual, r = comparar(t, t.copy())
    assert r["meses"] == 12 and r["correlacao"] == 1.0 and not r["sinal_invertido"]
    assert anual.loc[2024, "dif"] == 0 and anual.loc[2024, "dif_pct"] == 0


def test_comparar_detecta_sinal_invertido_e_diferenca():
    t = _serie([100.0, 120.0, 90.0, 110.0])
    bcb = -_serie([110.0, 130.0, 100.0, 120.0])  # BC com sinal oposto e 10 a mais por mês
    anual, r = comparar(t, bcb)
    assert r["sinal_invertido"] is True
    assert anual.loc[2024, "dif"] == -40.0
    assert r["meses_com_dif_acima_de_5pct"] == 4
