import pytest

from pipeline.tesouro import RESOURCE_ID, escolher_recurso


def test_escolher_recurso_pelo_id():
    pacote = {
        "result": {
            "resources": [
                {"id": "outro", "url": "https://exemplo/outro.xlsx"},
                {"id": RESOURCE_ID, "url": "https://exemplo/seriehistoricajul26.xlsx"},
            ]
        }
    }
    assert escolher_recurso(pacote).endswith("seriehistoricajul26.xlsx")


def test_escolher_recurso_inexistente():
    with pytest.raises(LookupError):
        escolher_recurso({"result": {"resources": []}})


import datetime as dt

import numpy as np
import pandas as pd

from pipeline.tesouro import limpar_rotulo, normalizar_aba


def test_limpar_rotulo():
    assert limpar_rotulo("1.1.03.3.1    IRRF - Rendimentos do Trabalho") == (
        "1.1.03.3.1", 5, "IRRF - Rendimentos do Trabalho")
    assert limpar_rotulo("1.1 -  Receita Administrada pela RFB") == (
        "1.1", 2, "Receita Administrada pela RFB")
    assert limpar_rotulo("9. JUROS NOMINAIS 13/") == ("9", 1, "JUROS NOMINAIS")
    assert limpar_rotulo("1. RECEITA TOTAL1/") == ("1", 1, "RECEITA TOTAL")
    assert limpar_rotulo("Custeio Administrativo") == (None, None, "Custeio Administrativo")


def _aba_sintetica() -> pd.DataFrame:
    meses = [dt.datetime(2026, m, 1) for m in (1, 2, 3, 4)]
    nan = np.nan
    return pd.DataFrame([
        ["Voltar", nan, nan, nan, nan],
        ["Tabela 1.2-A Resultado Primário", nan, nan, nan, nan],
        ["R$ Milhões - Valores de Jul/2026 - IPCA", nan, nan, nan, nan],
        [nan, nan, nan, nan, nan],
        ["Discriminação", *meses],
        ["1. RECEITA TOTAL 1/", 1, 2, 3, 4],
        ["4.2.1 Sent. Judiciais e Precatórios de Pessoal", 5, 6, 7, 8],
        ["9. JUROS NOMINAIS 13/", -1, -2, -3, nan],
        ["Obs.: Dados sujeitos à alteração.", nan, nan, nan, nan],
    ])


def test_normalizar_aba_sintetica():
    df = normalizar_aba(_aba_sintetica(), "1.2-A")
    assert len(df) == 4 + 4 + 3  # NaN e notas de rodapé são descartados
    assert set(df["base"]) == {"constante_ipca"}
    assert set(df["referencia"]) == {"Jul/2026"}
    juros = df[df["descricao"] == "JUROS NOMINAIS"]
    assert juros["codigo"].iloc[0] == "9" and list(juros["valor"]) == [-1, -2, -3]
    assert df[df["codigo"] == "4.2.1"]["nivel"].iloc[0] == 3
    assert not df.duplicated(["tabela", "ordem", "data"]).any()


def test_normalizar_aba_corrente_sem_referencia():
    bruto = _aba_sintetica()
    bruto.iloc[2, 0] = "R$ Milhões - Valores Correntes"
    df = normalizar_aba(bruto, "1.2")
    assert set(df["base"]) == {"corrente"} and df["referencia"].isna().all()


import pytest

from pipeline import tesouro as T


def test_baixar_usa_arquivo_manual_quando_o_site_recusa(tmp_path, monkeypatch, capsys):
    manual = tmp_path / "manual.xlsx"
    manual.write_bytes(b"xlsx de reserva")
    monkeypatch.setattr(T, "resolver_url", lambda: (_ for _ in ()).throw(RuntimeError("Download falhou 5 vezes")))
    destino = T.baixar(tmp_path / "raw" / "t.xlsx", manual)
    assert destino.read_bytes() == b"xlsx de reserva"
    assert "::warning" in capsys.readouterr().out


def test_baixar_sem_arquivo_manual_repassa_o_erro(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "resolver_url", lambda: (_ for _ in ()).throw(RuntimeError("Download falhou 5 vezes")))
    with pytest.raises(RuntimeError, match="5 vezes"):
        T.baixar(tmp_path / "t.xlsx", tmp_path / "nao_existe.xlsx")
