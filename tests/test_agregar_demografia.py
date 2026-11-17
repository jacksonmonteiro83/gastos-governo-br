import pandas as pd

from pipeline.agregar_demografia import agregar, ler_quinquenal


def _bruto():
    cab = ["GRUPO ETÁRIO", "SEXO", "CÓD.", "SIGLA", "LOCAL", 2000, 2001.0]
    linhas = [["Projeções das Populações, Revisão 2024"] + [None] * 6, [None] * 7, cab]
    pops = {"00-04": 100, "10-14": 100, "15-19": 200, "60-64": 200, "65-69": 50, "90+": 50}
    for g, v in pops.items():
        linhas.append([g, "Ambos", 0, "BR", "Brasil", v, v * 2.0])
        linhas.append([g, "Homens", 0, "BR", "Brasil", 1, 1.0])     # ignorado
        linhas.append([g, "Ambos", 53, "DF", "Distrito Federal", 9, 9.0])  # ignorado
    return pd.DataFrame(linhas)


def test_ler_e_agregar():
    longo = ler_quinquenal(_bruto())
    assert sorted(longo["ano"].unique()) == [2000, 2001]
    r = agregar(longo)
    # 2000: jovens 200, ativa 400, idosos 100 -> razão 25 por 100; 2001 dobra tudo (mesma razão)
    assert r["razao_idosos"] == [25.0, 25.0]
    assert r["pct_idosos"] == [round(100 * 100 / 700, 1)] * 2
    assert r["pessoas_ativas_por_idoso"] == [4.0, 4.0]


def test_sem_cabecalho():
    import pytest
    with pytest.raises(ValueError):
        ler_quinquenal(pd.DataFrame([["x", 1], ["y", 2]]))
