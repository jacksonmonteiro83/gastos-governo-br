import pandas as pd

from pipeline.bcb import parse_sgs


def test_parse_sgs_converte_tipos_e_ordena():
    registros = [
        {"data": "01/02/2020", "valor": "0.25"},
        {"data": "01/01/2020", "valor": "0.21"},
    ]
    df = parse_sgs(registros)
    assert list(df.columns) == ["data", "valor"]
    assert df["data"].is_monotonic_increasing
    assert df["data"].iloc[0] == pd.Timestamp("2020-01-01")
    assert df["valor"].iloc[0] == 0.21


def test_parse_sgs_vazio():
    assert parse_sgs([]).empty
