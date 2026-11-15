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
