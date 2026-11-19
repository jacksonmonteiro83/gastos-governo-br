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


import pytest
import requests

from pipeline.bcb import get_com_retentativas


class _Resp:
    def __init__(self, codigo):
        self.status_code = codigo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _get_sequencia(*respostas):
    fila = list(respostas)

    def get(url, params=None, timeout=None):
        r = fila.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    return get


def test_retenta_502_e_acaba_funcionando():
    pausas = []
    r = get_com_retentativas("u", {}, get=_get_sequencia(_Resp(502), _Resp(502), _Resp(200)), dormir=pausas.append)
    assert r.status_code == 200 and pausas == [5.0, 10.0]


def test_retenta_erro_de_rede():
    r = get_com_retentativas("u", {}, get=_get_sequencia(requests.ConnectionError(), _Resp(200)), dormir=lambda s: None)
    assert r.status_code == 200


def test_desiste_depois_de_n_tentativas():
    with pytest.raises(RuntimeError, match="3 vezes"):
        get_com_retentativas("u", {}, tentativas=3, get=_get_sequencia(_Resp(502), _Resp(503), _Resp(502)), dormir=lambda s: None)


def test_404_nao_retenta():
    with pytest.raises(requests.HTTPError):
        get_com_retentativas("u", {}, get=_get_sequencia(_Resp(404)), dormir=lambda s: pytest.fail("não devia dormir"))
