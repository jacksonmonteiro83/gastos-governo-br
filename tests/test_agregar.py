import pandas as pd

from pipeline.agregar import agregar, anular_zeros_iniciais


def test_anular_zeros_iniciais():
    s = pd.Series([0.0, 0.0, 5.0, 0.0, 7.0], index=[2000, 2001, 2002, 2003, 2004])
    r = anular_zeros_iniciais(s)
    assert r.isna().tolist() == [True, True, False, False, False]
    assert r.loc[2003] == 0.0  # zero depois do início é valor real


def _linha(codigo, nivel, desc, data, valor):
    return {"tabela": "1.2-A", "base": "constante_ipca", "referencia": "Jul/2026", "data": data,
            "ordem": 0, "codigo": codigo, "nivel": nivel, "descricao": desc,
            "rotulo_original": desc, "valor": valor}


def test_agregar_soma_anual_e_sinal_dos_juros():
    linhas = []
    for ano in (2024, 2025):
        for mes in range(1, 13):
            d = f"{ano}-{mes:02d}-01"
            linhas += [
                _linha("9", 1, "JUROS NOMINAIS", d, -100.0),
                _linha("4.1", 2, "Benefícios", d, 10.0),
                _linha("4.2", 2, "Pessoal", d, 20.0),
                _linha("4.3", 2, "Outras", d, 30.0),
                _linha("4.4", 2, "Executivo", d, 40.0),
                _linha("4.4.1.3", 4, "Saúde", d, 5.0),
                _linha("4.4.2.1", 4, "Saúde", d, 5.0),
                _linha("4.4.1.4", 4, "Educação", d, 2.0),
                _linha("4.4.2.2", 4, "Educação", d, 1.0),
                _linha(None, None, "Investimento", d, 3.0),
                _linha("4", 1, "DESPESA TOTAL", d, 100.0),
            ]
    r = agregar(pd.DataFrame(linhas))
    assert r["anos"] == [2024, 2025] and r["meses"] == [12, 12]
    assert r["series"]["juros"]["valores"] == [1.2, 1.2]       # 100 * 12 / 1000, sinal invertido
    assert r["series"]["saude"]["valores"] == [0.12, 0.12]      # dois códigos somados
    assert r["series"]["educacao"]["valores"] == [0.04, 0.04]
    assert r["destaques"]["ano_referencia"] == 2025
    assert r["destaques"]["juros_pct_gasto_total"] == 50.0      # 1,2 / (1,2 + 1,2)
