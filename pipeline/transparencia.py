"""Portal da Transparência: orçamento e execução da despesa federal, por ano.

Escolha de dado: a página "Despesas" do portal entrega documentos de empenho/liquidação/pagamento,
com favorecidos (inclusive pessoas físicas) e arquivos enormes. Para a pergunta "para onde vai o
dinheiro" usamos o arquivo anual do ORÇAMENTO DA DESPESA, já agregado por órgão, função, programa e
ação, com orçamento inicial/atualizado e valores empenhado, realizado (liquidado) e pago. Sem favorecidos.

Uso:
    python -m pipeline.transparencia --inspecionar 2023   # baixa um ano e mostra colunas e amostra
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

URL_BASE = "https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/"
DESTINO = RAW_DIR / "orcamento_despesa"


def url_ano(ano: int) -> str:
    return f"{URL_BASE}{ano}"


def baixar_ano(ano: int, pasta: Path = DESTINO) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{ano}.zip"
    if destino.exists() and zipfile.is_zipfile(destino):
        return destino
    r = requests.get(url_ano(ano), timeout=600)
    print(f"GET {url_ano(ano)} -> HTTP {r.status_code}, {r.headers.get('content-type')}, {len(r.content):,} bytes")
    r.raise_for_status()
    destino.write_bytes(r.content)
    if not zipfile.is_zipfile(destino):
        raise ValueError(f"{destino} não é um ZIP: o portal devolveu outra coisa (início: {r.content[:200]!r})")
    return destino


def ler_csv(zf: zipfile.ZipFile, nome: str, **kw) -> pd.DataFrame:
    with zf.open(nome) as f:
        for enc in ("utf-8-sig", "latin-1"):
            f.seek(0)
            try:
                return pd.read_csv(f, sep=";", encoding=enc, dtype=str, **kw)
            except UnicodeDecodeError:
                continue
    raise ValueError(f"Não consegui decodificar {nome}")


def inspecionar(ano: int) -> None:
    caminho = baixar_ano(ano)
    with zipfile.ZipFile(caminho) as zf:
        print("Arquivos no ZIP:", [(i.filename, f"{i.file_size:,} bytes") for i in zf.infolist()])
        for nome in zf.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            df = ler_csv(zf, nome)
            print(f"\n=== {nome} === {len(df):,} linhas x {df.shape[1]} colunas")
            print("Colunas:", list(df.columns))
            with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_colwidth", 30):
                print(df.head(5).to_string())
            # colunas com poucos valores distintos ajudam a entender as dimensões
            for c in df.columns:
                n = df[c].nunique()
                if n <= 25:
                    print(f"  {c}: {n} valores -> {sorted(df[c].dropna().unique())[:25]}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--inspecionar" in sys.argv and args:
        inspecionar(int(args[0]))
    else:
        raise SystemExit("Uso: python -m pipeline.transparencia --inspecionar AAAA")


if __name__ == "__main__":
    main()
