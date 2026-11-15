"""Tesouro Transparente: Resultado do Tesouro Nacional (série mensal desde 1997).

O XLSX muda de nome todo mês (ex.: seriehistoricajul26.xlsx), mas o id do recurso
no CKAN é estável. Por isso resolvemos a URL atual pela API do CKAN.

Uso:
    python -m pipeline.tesouro               # baixa o XLSX para data/raw
    python -m pipeline.tesouro --inspecionar # lista abas e primeiras linhas

PRÓXIMO PASSO: com a saída de --inspecionar, escrever `normalizar()` para
transformar as abas em formato longo (data, codigo_serie, descricao, valor).
"""
import sys
from pathlib import Path

import requests

from pipeline.config import RAW_DIR

CKAN_PACKAGE_SHOW = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
DATASET_ID = "ab56485b-9c40-4efb-8563-9ce3e1973c4b"
RESOURCE_ID = "527ccdb1-3059-42f3-bf23-b5e3ab4c6dc6"  # Série Histórica - Mensal (XLSX)
DESTINO = RAW_DIR / "tesouro_serie_historica.xlsx"


def escolher_recurso(pacote: dict, resource_id: str = RESOURCE_ID) -> str:
    """Devolve a URL de download do recurso dentro da resposta do package_show."""
    for recurso in pacote["result"]["resources"]:
        if recurso["id"] == resource_id:
            return recurso["url"]
    raise LookupError(f"Recurso {resource_id} não encontrado no dataset.")


def resolver_url() -> str:
    r = requests.get(CKAN_PACKAGE_SHOW, params={"id": DATASET_ID}, timeout=60)
    r.raise_for_status()
    return escolher_recurso(r.json())


def baixar(destino: Path = DESTINO) -> Path:
    url = resolver_url()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for bloco in r.iter_content(chunk_size=1 << 20):
                f.write(bloco)
    print(f"Baixado: {url}\n -> {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
    return destino


def inspecionar(caminho: Path = DESTINO, linhas: int = 6) -> None:
    import pandas as pd

    xls = pd.ExcelFile(caminho)
    for aba in xls.sheet_names:
        df = xls.parse(aba, header=None, nrows=200)
        print(f"\n=== {aba} === (amostra: {df.shape[0]} linhas x {df.shape[1]} colunas)")
        print(df.iloc[:linhas, :6].to_string())


def main() -> None:
    if "--inspecionar" in sys.argv:
        if not DESTINO.exists():
            baixar()
        inspecionar()
    else:
        baixar()


if __name__ == "__main__":
    main()
