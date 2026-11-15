"""Portal da Transparência: Cartão de Pagamento do Governo Federal (CPGF), dados mensais.

Uso:
    python -m pipeline.cpgf 202401               # baixa um mês (AAAAMM)
    python -m pipeline.cpgf --inspecionar 202401 # baixa e mostra arquivos, colunas e amostra

ATENÇÃO: o padrão da URL por mês (`.../download-de-dados/cpgf/AAAAMM`) ainda NÃO foi
confirmado a partir daqui (a rede do ambiente de desenvolvimento não alcança o portal).
Use o workflow "Inspecionar CPGF" no GitHub para validar antes de construir em cima.
"""
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

URL_BASE = "https://portaldatransparencia.gov.br/download-de-dados/cpgf/"
DESTINO = RAW_DIR / "cpgf"
# Os CSVs do portal costumam vir em latin-1, separados por ponto e vírgula.
ENCODINGS = ("utf-8-sig", "latin-1")


def url_mes(ano: int, mes: int) -> str:
    if not 1 <= mes <= 12:
        raise ValueError("mês deve estar entre 1 e 12")
    return f"{URL_BASE}{ano}{mes:02d}"


def baixar_mes(ano: int, mes: int, pasta: Path = DESTINO) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{ano}{mes:02d}.zip"
    with requests.get(url_mes(ano, mes), stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for bloco in r.iter_content(chunk_size=1 << 20):
                f.write(bloco)
    if not zipfile.is_zipfile(destino):
        raise ValueError(f"{destino} não é um ZIP: o portal pode ter devolvido uma página HTML.")
    print(f"Baixado: {url_mes(ano, mes)} -> {destino} ({destino.stat().st_size / 1e6:.2f} MB)")
    return destino


def ler_csv(zf: zipfile.ZipFile, nome: str, **kw) -> pd.DataFrame:
    bruto = zf.read(nome)
    ultimo_erro = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(bruto), sep=";", encoding=enc, dtype=str, **kw)
        except UnicodeDecodeError as e:
            ultimo_erro = e
    raise ultimo_erro


def inspecionar(ano: int, mes: int) -> None:
    caminho = baixar_mes(ano, mes)
    with zipfile.ZipFile(caminho) as zf:
        print("Arquivos no ZIP:", zf.namelist())
        for nome in zf.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            df = ler_csv(zf, nome)
            print(f"\n=== {nome} === {len(df):,} linhas x {df.shape[1]} colunas")
            print("Colunas:", list(df.columns))
            print(df.head(5).to_string())


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("Uso: python -m pipeline.cpgf [--inspecionar] AAAAMM")
    ano, mes = int(args[0][:4]), int(args[0][4:])
    if "--inspecionar" in sys.argv:
        inspecionar(ano, mes)
    else:
        baixar_mes(ano, mes)


if __name__ == "__main__":
    main()
