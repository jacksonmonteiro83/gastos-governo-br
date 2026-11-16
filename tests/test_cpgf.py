import io
import zipfile

import pytest

from pipeline.cpgf import ler_csv, url_mes


def test_url_mes():
    assert url_mes(2024, 1).endswith("/download-de-dados/cpgf/202401")
    with pytest.raises(ValueError):
        url_mes(2024, 13)


def test_ler_csv_latin1_ponto_e_virgula():
    conteudo = "NOME FAVORECIDO;VALOR TRANSAÇÃO\nPADARIA AÇÚCAR;1.234,56\n".encode("latin-1")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("202401_CPGF.csv", conteudo)
    with zipfile.ZipFile(buf) as zf:
        df = ler_csv(zf, "202401_CPGF.csv")
    assert list(df.columns) == ["NOME FAVORECIDO", "VALOR TRANSAÇÃO"]
    assert df.iloc[0, 0] == "PADARIA AÇÚCAR"


import pandas as pd

from pipeline.cpgf import meses, normalizar_mes


def _bruto():
    cols = ["CÓDIGO ÓRGÃO SUPERIOR", "NOME ÓRGÃO SUPERIOR", "CÓDIGO ÓRGÃO", "NOME ÓRGÃO",
            "CÓDIGO UNIDADE GESTORA", "NOME UNIDADE GESTORA", "ANO EXTRATO", "MÊS EXTRATO",
            "CPF PORTADOR", "NOME PORTADOR", "CNPJ OU CPF FAVORECIDO", "NOME FAVORECIDO",
            "TRANSAÇÃO", "DATA TRANSAÇÃO", "VALOR TRANSAÇÃO"]
    base = ["63000", "AGU", "63000", "AGU", "110161", "SUPERINTENDENCIA", "2024", "01",
            "***.866.951-**", "FULANO DE TAL"]
    return pd.DataFrame([
        [*base, "05471879000173", "KASA MOTORS LTDA", "COMPRA A/V - R$ - APRES", "29/11/2023", "1.234,56"],
        [*base, "***.184.246-**", "CLEUSA JOSE DA SILVA", "SAQUE CASH/ATM BB", "01/12/2023", "100,00"],
        [*base, "-2", "Sigiloso", "Informações protegidas por sigilo", None, "50,00"],
        [*base, "12345678000199", "JOAO PEREIRA DE MOURA 32283261287", "COMPRA A/V - R$ - APRES", "02/12/2023", "10,00"],
    ], columns=cols)


def test_normalizar_mes_valores_e_tipos():
    out = normalizar_mes(_bruto())
    assert out["valor"].tolist() == [1234.56, 100.0, 50.0, 10.0]
    assert out["tipo_transacao"].tolist() == ["compra", "saque", "sigilo", "compra"]
    assert out["sigiloso"].tolist() == [False, False, True, False]
    assert out["favorecido_tipo"].tolist() == ["pj", "pf", "sem_informacao", "mei"]
    assert out["data_transacao"].isna().tolist() == [False, False, True, False]


def test_normalizar_mes_nao_guarda_pessoas():
    out = normalizar_mes(_bruto())
    assert "nome_portador" not in out.columns and "cpf_portador" not in out.columns
    assert out["favorecido_nome"].iloc[0] == "KASA MOTORS LTDA"
    assert out["favorecido_nome"].iloc[1:].isna().all()  # PF, sigilo e MEI ficam anônimos
    assert out["favorecido_cnpj"].iloc[0] == "05471879000173"
    assert out["favorecido_cnpj"].iloc[1:].isna().all()


def test_meses_intervalo():
    assert list(meses((2023, 11), (2024, 2))) == [(2023, 11), (2023, 12), (2024, 1), (2024, 2)]
