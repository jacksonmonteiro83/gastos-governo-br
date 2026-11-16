import pandas as pd

from pipeline.agregar_previdencia import agregar


def _l(tab, codigo, nivel, desc, data, valor):
    return {"tabela": tab, "referencia": "Jul/2026", "data": data, "codigo": codigo,
            "nivel": nivel, "descricao": desc, "valor": valor}


def _base():
    linhas = []
    for ano in (2009, 2010, 2011):
        for mes in range(1, 13):
            d = f"{ano}-{mes:02d}-01"
            for tab, k in (("1.2-A", 1.0), ("1.2", 0.5)):
                linhas += [
                    _l(tab, "1.3", 2, "Arrecadação Líquida para o RGPS", d, 600 * k),
                    _l(tab, "4.1", 2, "Benefícios Previdenciários", d, 1000 * k),
                    _l(tab, "4", 1, "DESPESA TOTAL", d, 2500 * k),
                ]
    return pd.DataFrame(linhas)


def test_necessidade_cobertura_e_pib():
    # série mensal completa (como no SGS): só dezembro deve ser usado
    pib = pd.DataFrame({"data": [f"{a}-{m:02d}-01" for a in (2010, 2011) for m in range(1, 13)],
                        "valor": [1.0] * 11 + [20000.0] + [1.0] * 11 + [10000.0]})
    r = agregar(_base(), pib)
    assert r["anos"] == [2009, 2010, 2011] and r["meses"] == [12, 12, 12]
    assert r["arrecadacao"][0] == 7.2 and r["beneficios"][0] == 12.0   # 600*12/1000 e 1000*12/1000
    assert r["necessidade"][0] == 4.8
    assert r["cobertura_pct"][0] == 60.0
    assert r["beneficios_pct_despesa_primaria"][0] == 40.0
    assert r["pct_pib_necessidade"] == [None, 12.0, 24.0]  # (6000-3600)/PIB de dezembro; 2009 sem PIB
    assert r["destaques"]["ano_referencia"] == 2011
    assert r["destaques"]["beneficios_crescimento_real_desde_2010_pct"] == 0.0


def test_sem_pib():
    r = agregar(_base(), None)
    assert r["pct_pib_necessidade"] == [None, None, None]
