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
