import pandas as pd

from pipeline.agregar_cpgf import agregar, fator_ipca


def _ipca(meses=24, taxa=1.0):
    return pd.DataFrame({"data": pd.date_range("2023-01-01", periods=meses, freq="MS"),
                         "valor": [taxa] * meses})


def test_fator_ipca_ultimo_mes_vale_um():
    f = fator_ipca(_ipca())
    assert f.iloc[-1] == 1.0
    assert abs(f.iloc[0] - 1.01 ** 23) < 1e-9  # jan/2023 -> dez/2024, 23 correções


def _linha(ano, mes, tipo, valor, fav="pj", cnpj="11111111000111", nome="EMPRESA A", orgao="Ministério X"):
    return {"ano_extrato": ano, "mes_extrato": mes, "tipo_transacao": tipo, "valor": valor,
            "favorecido_tipo": fav, "favorecido_cnpj": cnpj if fav == "pj" else None,
            "favorecido_nome": nome if fav == "pj" else None, "orgao_superior": orgao}


def test_agregar_totais_e_percentuais():
    linhas = []
    for ano in (2023, 2024):
        for mes in range(1, 13):
            linhas += [_linha(ano, mes, "compra", 100.0),
                       _linha(ano, mes, "saque", 50.0, fav="sem_informacao"),
                       _linha(ano, mes, "sigilo", 50.0, fav="sem_informacao")]
    r = agregar(pd.DataFrame(linhas), _ipca())
    assert r["anos"] == [2023, 2024] and r["meses"] == [12, 12]
    # 2024 (mais recente): sem correção relevante em dez; sigilo é 25% e saque 25%
    assert r["destaques"]["ano_referencia"] == 2024
    assert r["destaques"]["sigilo_pct"] == 25.0 and r["destaques"]["saque_pct"] == 25.0
    assert r["compra"][1] > 0 and r["compra"][0] > r["compra"][1] * 0.99  # 2023 corrigido para cima
    assert r["empresas"][0]["nome"] == "EMPRESA A" and r["empresas"][0]["transacoes"] == 24
    assert r["orgaos"][0]["nome"] == "Ministério X"


def test_agregar_nao_expoe_pessoas():
    linhas = [_linha(2024, m, "compra", 10.0, fav="pf") for m in range(1, 13)]
    r = agregar(pd.DataFrame(linhas), _ipca())
    assert r["empresas"] == []
