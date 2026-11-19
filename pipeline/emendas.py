"""Portal da Transparência: emendas parlamentares (CGU), arquivo único com todos os anos desde 2014.

Esta etapa é só INSPEÇÃO: baixa o ZIP, lista os arquivos e mostra colunas, amostra e dimensões
(quem é o autor, tipo de emenda, valores empenhado/liquidado/pago, localidade do gasto) para decidir
o que agregar antes de escrever o pipeline de verdade.

    python -m pipeline.emendas --inspecionar   # colunas e amostra de cada arquivo do ZIP
    python -m pipeline.emendas --tudo          # baixa e gera data/raw/emendas.parquet

Só o arquivo principal (EmendasParlamentares.csv, uma linha por emenda x localidade x ação) vira Parquet.
Os arquivos por favorecido e por plano de trabalho ficam de fora: são enormes e trazem beneficiários finais.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR
from pipeline.transparencia import _numero, _slug, ler_csv

URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
DESTINO = RAW_DIR / "emendas"
SAIDA = RAW_DIR / "emendas.parquet"
PRINCIPAL = "EmendasParlamentares.csv"
# slug exato da coluna do CSV -> nome na saída
_COLUNAS = {
    "codigo_da_emenda": "codigo", "ano_da_emenda": "ano", "tipo_de_emenda": "tipo",
    "codigo_do_autor_da_emenda": "autor_cod", "nome_do_autor_da_emenda": "autor",
    "possui_apoiador_solicitante": "apoiador", "uf": "uf", "regiao": "regiao", "municipio": "municipio",
    "nome_funcao": "funcao", "nome_subfuncao": "subfuncao",
    "valor_empenhado": "empenhado", "valor_liquidado": "liquidado", "valor_pago": "pago",
    "valor_restos_a_pagar_inscritos": "rap_inscrito", "valor_restos_a_pagar_cancelados": "rap_cancelado",
    "valor_restos_a_pagar_pagos": "rap_pago",
}
_VALORES = ["empenhado", "liquidado", "pago", "rap_inscrito", "rap_cancelado", "rap_pago"]


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """CSV cru de emendas -> colunas padronizadas; valores em R$ nominais (numéricos)."""
    achadas = {}
    for original in df.columns:
        destino = _COLUNAS.get(_slug(original))
        if destino:
            achadas.setdefault(destino, original)
    faltam = [d for d in ("ano", "tipo", "autor", "uf", "empenhado", "pago") if d not in achadas]
    if faltam:
        raise ValueError(f"Colunas não encontradas: {faltam}. Colunas do arquivo: {list(df.columns)}")
    out = pd.DataFrame({d: df[o] for d, o in achadas.items()})
    for c in _VALORES:
        if c in out:
            out[c] = _numero(out[c].astype("string"))
    out["ano"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int64")
    for c in out.columns:
        if c not in _VALORES and c != "ano":
            out[c] = out[c].astype("string").str.strip()
    return out.dropna(subset=["ano", "empenhado"]).reset_index(drop=True)


def consolidar(saida: Path = SAIDA) -> pd.DataFrame:
    with zipfile.ZipFile(baixar(forcar=True)) as zf:
        df = normalizar(ler_csv(zf, PRINCIPAL))
    saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(saida, index=False)
    print(f"{len(df):,} linhas, anos {int(df['ano'].min())}-{int(df['ano'].max())} -> {saida}")
    return df


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
    if "--tudo" in sys.argv:
        consolidar()
    elif "--inspecionar" in sys.argv:
        inspecionar()
    else:
        raise SystemExit("Uso: python -m pipeline.emendas --inspecionar | --tudo")
