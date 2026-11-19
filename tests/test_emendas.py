import pandas as pd

from pipeline.agregar_emendas import agregar
from pipeline.emendas import normalizar

ESP = "Emenda Individual - Transferências Especiais"
FIN = "Emenda Individual - Transferências com Finalidade Definida"


def _bruto():
    return pd.DataFrame({
        "Código da Emenda": ["1", "2"], "Ano da Emenda": ["2024", "2024"], "Tipo de Emenda": [ESP, "Emenda de Relator"],
        "Nome do Autor da Emenda": ["FULANA", "Sem informação"], "UF": ["CE", "SP"], "Região": ["Nordeste", "Sudeste"],
        "Nome Função": ["Saúde", "Educação"],
        "Valor Empenhado": ["1.000,50", "200,00"], "Valor Liquidado": ["0,00", "0,00"], "Valor Pago": ["500,25", "0,00"],
        "Valor Restos A Pagar Pagos": ["0,00", "100,00"],
    })


def test_normalizar_numeros_e_colunas():
    n = normalizar(_bruto())
    assert n["empenhado"].tolist() == [1000.5, 200.0] and n["ano"].tolist() == [2024, 2024]
    assert {"tipo", "autor", "uf", "regiao", "funcao", "rap_pago"} <= set(n.columns)


def _df():
    L = []
    for ano in (2023, 2024):
        L += [dict(ano=ano, tipo=ESP, autor="FULANA", uf="CE", regiao="Nordeste", funcao="Saúde", empenhado=300e9, pago=150e9, rap_pago=0.0),
              dict(ano=ano, tipo=FIN, autor="BELTRANO", uf="SP", regiao="Sudeste", funcao="Educação", empenhado=100e9, pago=100e9, rap_pago=0.0),
              dict(ano=ano, tipo="Emenda de Relator", autor="Sem informação", uf="SP", regiao="Sudeste", funcao="Saúde", empenhado=100e9, pago=0.0, rap_pago=50e9),
              dict(ano=ano, tipo="Emenda de Comissão", autor="Comissão X", uf="Múltiplo", regiao="Múltiplo", funcao="Saúde", empenhado=0.0, pago=0.0, rap_pago=0.0)]
    return pd.DataFrame(L)


def test_agregar_totais_e_destaques():
    r = agregar(_df(), None, ano_corrente=2025)
    assert r["anos"] == [2023, 2024] and r["total_bi"] == [500.0, 500.0]
    h = r["destaques"]
    assert h["ano_referencia"] == 2024 and h["especial_pct"] == 60.0 and h["individual_pct"] == 80.0
    assert h["autor_identificado_pct"] == 80.0       # só o relator ficou sem autor
    assert h["relator_total_bi"] == 200.0 and h["executado_pct"] == 60.0   # (150+100+0+50)/500
    assert r["ref_por_autor"][0]["nome"] == "FULANA" and r["ref_por_uf"][0]["nome"] == "CE"
    assert all(x["nome"] != "Múltiplo" for x in r["ref_por_uf"])


def test_ano_corrente_parcial_nao_e_referencia():
    df = pd.concat([_df(), _df().assign(ano=2025)], ignore_index=True)
    r = agregar(df, None, ano_corrente=2025)
    assert r["ano_corrente_parcial"] is True and r["destaques"]["ano_referencia"] == 2024
