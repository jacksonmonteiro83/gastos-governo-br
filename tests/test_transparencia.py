import pandas as pd
import pytest

from pipeline.transparencia import _numero, normalizar


def _cru(sem=()):
    cab = ["EXERCÍCIO", "CÓDIGO ÓRGÃO SUPERIOR", "NOME ÓRGÃO SUPERIOR", "CÓDIGO FUNÇÃO", "NOME FUNÇÃO",
           "CÓDIGO SUBFUNÇÃO", "NOME SUBFUNÇÃO", "CÓDIGO AÇÃO", "NOME AÇÃO", "NOME CATEGORIA ECONÔMICA",
           "CÓDIGO GRUPO DE DESPESA", "NOME GRUPO DE DESPESA", "NOME ELEMENTO DE DESPESA",
           "ORÇAMENTO INICIAL (R$)", "ORÇAMENTO ATUALIZADO (R$)", "ORÇAMENTO EMPENHADO (R$)",
           "ORÇAMENTO REALIZADO (R$)", "% REALIZADO DO ORÇAMENTO (COM RELAÇÃO AO ORÇAMENTO ATUALIZADO)"]
    linha = ["2023", "20000", "Presidência da República", "04", "Administração", "122", "Administração geral",
             "2000", "ADMINISTRACAO DA UNIDADE", "DESPESAS CORRENTES", "3", "Outras Despesas Correntes",
             "Material de Consumo", "0,00", "1.234,50", "3879,21", "2069,00", "90,08%"]
    return pd.DataFrame([linha], columns=cab).drop(columns=list(sem))


def test_numero_pt_br():
    r = _numero(pd.Series(["3879,21", "1.234,50", "0,00", "3642593,00"], dtype="string"))
    assert r.tolist() == [3879.21, 1234.5, 0.0, 3642593.0]


def test_normalizar_layout_2023():
    r = normalizar(_cru())
    assert r.loc[0, "ano"] == 2023 and r.loc[0, "funcao"] == "Administração"
    assert r.loc[0, "atualizado"] == 1234.5 and r.loc[0, "realizado"] == 2069.0
    assert r.loc[0, "orgao_superior"] == "Presidência da República" and r.loc[0, "grupo_cod"] == "3"
    assert not any("realizado_do" in c for c in r.columns)  # a coluna de % não entra


def test_layout_diferente_falha_com_mensagem():
    with pytest.raises(ValueError, match="realizado"):
        normalizar(_cru(sem=["ORÇAMENTO REALIZADO (R$)"]))
