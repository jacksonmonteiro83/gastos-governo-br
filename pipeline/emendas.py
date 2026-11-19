"""Portal da Transparência: emendas parlamentares (CGU), arquivo único com todos os anos desde 2014.

Esta etapa é só INSPEÇÃO: baixa o ZIP, lista os arquivos e mostra colunas, amostra e dimensões
(quem é o autor, tipo de emenda, valores empenhado/liquidado/pago, localidade do gasto) para decidir
o que agregar antes de escrever o pipeline de verdade.

    python -m pipeline.emendas --inspecionar
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR
from pipeline.transparencia import ler_csv

URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
DESTINO = RAW_DIR / "emendas"


def baixar(forcar: bool = False) -> Path:
    DESTINO.mkdir(parents=True, exist_ok=True)
    destino = DESTINO / "emendas.zip"
    if not forcar and destino.exists() and zipfile.is_zipfile(destino):
        return destino
    r = requests.get(URL, timeout=600)
    print(f"GET {URL} -> HTTP {r.status_code}, {r.headers.get('content-type')}, {len(r.content):,} bytes")
    r.raise_for_status()
    destino.write_bytes(r.content)
    if not zipfile.is_zipfile(destino):
        raise ValueError(f"não é um ZIP; início da resposta: {r.content[:300]!r}")
    return destino


def inspecionar() -> None:
    with zipfile.ZipFile(baixar()) as zf:
        print("Arquivos no ZIP:", [(i.filename, f"{i.file_size:,} bytes") for i in zf.infolist()])
        for nome in zf.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            df = ler_csv(zf, nome)
            print(f"\n=== {nome} === {len(df):,} linhas x {df.shape[1]} colunas")
            print("Colunas:", list(df.columns))
            with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 30):
                print(df.head(5).to_string())
            for c in df.columns:
                n = df[c].nunique()
                if n <= 25:
                    print(f"  {c}: {n} valores -> {sorted(df[c].dropna().unique())[:25]}")


if __name__ == "__main__":
    if "--inspecionar" not in sys.argv:
        raise SystemExit("Uso: python -m pipeline.emendas --inspecionar")
    inspecionar()
