import pandas as pd

from pipeline.agregar_despesas import agregar


def _linha(ano, funcao, grupo_cod, grupo, orgao, realizado, atualizado=None):
    return dict(ano=ano, funcao=funcao, grupo_cod=grupo_cod, grupo=grupo, orgao_superior=orgao,
                realizado=realizado * 1e9, atualizado=(atualizado or realizado) * 1e9)


def _df():
    L = []
    for ano in (2022, 2023, 2024):
        L += [
            _linha(ano, "Previdência social", "1", "Pessoal e Encargos Sociais", "MPS", 100),
            _linha(ano, "Saúde", "3", "Outras Despesas Correntes", "MS", 50),
            _linha(ano, "Encargos especiais", "2", "Juros e Encargos da Dívida", "MF", 50),
            _linha(ano, "Encargos especiais", "6", "Amortização/Refinanciamento da Dívida", "MF", 1000),  # fora
            _linha(ano, "Reserva", "9", "Reserva de Contingência", "MF", 10),                              # fora
        ]
    return pd.DataFrame(L)


def test_exclui_amortizacao_e_reserva_e_calcula_pesos():
    r = agregar(_df(), None, ano_corrente=2025)
    assert r["anos"] == [2022, 2023, 2024] and r["ano_corrente_parcial"] is False
    assert r["total_bi"] == [200.0, 200.0, 200.0]
    h = r["destaques"]
    assert h["ano_referencia"] == 2024 and h["amortizacao_bi"] == 1000.0
    assert h["previdencia_pct"] == 50.0 and h["saude_pct"] == 25.0 and h["juros_pct"] == 25.0
    assert h["execucao_pct"] == 100.0
    assert r["funcoes"]["Previdência social"] == [100.0, 100.0, 100.0]
    assert r["orgaos_ano_ref"][0] == {"orgao": "MPS", "bi": 100.0, "pct": 50.0}


def test_ano_corrente_e_parcial_e_nao_e_referencia():
    r = agregar(_df(), None, ano_corrente=2024)
    assert r["ano_corrente_parcial"] is True
    assert r["destaques"]["ano_referencia"] == 2023


def test_deflaciona_pelo_ipca():
    ipca = pd.DataFrame({"data": [f"{a}-{m:02d}-01" for a in (2022, 2023, 2024) for m in range(1, 13)],
                         "valor": [1.0] * 36})  # 1% ao mês
    r = agregar(_df(), ipca, ano_corrente=2025)
    assert r["total_bi"][0] > r["total_bi"][2] > 200.0 - 1e-9  # anos antigos sobem mais


def test_composicao_sem_sobreposicao():
    r = agregar(_df(), None, ano_corrente=2025)
    c = r["composicao"]
    # previdência 100 + saúde 50 + juros 50 = 200 por ano
    assert c["Previdência social"][-1] == 50.0 and c["Juros da dívida"][-1] == 25.0
    assert c["Saúde, educação e assistência"][-1] == 25.0
    assert abs(sum(v[-1] for v in c.values()) - 100.0) < 0.2   # cada R$ entra em uma só categoria
    h = r["destaques"]
    assert h["trio_pct"] == 75.0 and h["trio_bi"] == 150.0


def test_categoria_prioridade():
    from pipeline.agregar_despesas import categoria
    assert categoria("Previdência social", "Pessoal e Encargos Sociais") == "Previdência social"
    assert categoria("Saúde", "Pessoal e Encargos Sociais") == "Pessoal e encargos"
    assert categoria("Saúde", "Outras Despesas Correntes") == "Saúde, educação e assistência"
    assert categoria("Transporte", "Investimentos") == "Investimentos"
    assert categoria("Defesa nacional", "Outras Despesas Correntes") == "Outras"


def test_outras_detalha_funcao_e_elemento():
    df = _df()
    df["elemento"] = "Outros"
    extra = pd.DataFrame([
        dict(_linha(2024, "Encargos especiais", "3", "Outras Despesas Correntes", "MF", 30), elemento="Transferências a Estados"),
        dict(_linha(2024, "Defesa nacional", "3", "Outras Despesas Correntes", "MD", 10), elemento="Material de consumo"),
    ])
    r = agregar(pd.concat([df, extra], ignore_index=True), None, ano_corrente=2025)["outras_ref"]
    assert r["total_bi"] == 40.0
    assert r["por_funcao"][0] == {"nome": "Encargos especiais", "bi": 30.0, "pct": 75.0}
    assert r["por_elemento"][0]["nome"] == "Transferências a Estados"
    assert sum(x["pct"] for x in r["por_funcao"]) == 100.0


def test_outras_sem_coluna_elemento():
    r = agregar(_df(), None, ano_corrente=2025)["outras_ref"]
    assert r["por_elemento"] == []
