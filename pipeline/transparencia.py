"""Portal da Transparência: orçamento e execução da despesa federal, por ano.

Escolha de dado: a página "Despesas" do portal entrega documentos de empenho/liquidação/pagamento,
com favorecidos (inclusive pessoas físicas) e arquivos enormes. Para a pergunta "para onde vai o
dinheiro" usamos o arquivo anual do ORÇAMENTO DA DESPESA, já agregado por órgão, função, programa e
ação, com orçamento inicial/atualizado e valores empenhado, realizado (liquidado) e pago. Sem favorecidos.

Uso:
    python -m pipeline.transparencia --inspecionar 2023   # baixa um ano e mostra colunas e amostra
    python -m pipeline.transparencia --tudo               # baixa 2014 até o ano atual e gera o Parquet

Os valores do arquivo são nominais do ano (R$) e usam vírgula decimal. "Orçamento realizado" é o
termo do portal para a despesa realizada no ano (liquidada).
"""
import datetime as dt
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

URL_BASE = "https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/"
DESTINO = RAW_DIR / "orcamento_despesa"
SAIDA = RAW_DIR / "orcamento_despesa.parquet"
PRIMEIRO_ANO = 2014
# O arquivo do ano corrente (e o do anterior, que ainda recebe ajustes) muda: nunca vem do cache.
ANOS_SEMPRE_ATUALIZADOS = 2


def url_ano(ano: int) -> str:
    return f"{URL_BASE}{ano}"


def baixar_ano(ano: int, pasta: Path = DESTINO, forcar: bool = False) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{ano}.zip"
    if not forcar and destino.exists() and zipfile.is_zipfile(destino):
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


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _numero(serie: pd.Series) -> pd.Series:
    """'3879,21' -> 3879.21 (aceita ponto de milhar)."""
    return pd.to_numeric(serie.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


# prefixo do nome slugificado da coluna do CSV -> nome na saída
_COLUNAS = {
    "exercicio": "ano",
    "codigo_orgao_superior": "orgao_superior_cod", "nome_orgao_superior": "orgao_superior",
    "codigo_orgao_subordinado": "orgao_cod", "nome_orgao_subordinado": "orgao",
    "codigo_funcao": "funcao_cod", "nome_funcao": "funcao",
    "codigo_subfuncao": "subfuncao_cod", "nome_subfuncao": "subfuncao",
    "codigo_acao": "acao_cod", "nome_acao": "acao",
    "codigo_categoria_economica": "categoria_cod", "nome_categoria_economica": "categoria",
    "codigo_grupo_de_despesa": "grupo_cod", "nome_grupo_de_despesa": "grupo",
    "codigo_elemento_de_despesa": "elemento_cod", "nome_elemento_de_despesa": "elemento",
    "orcamento_inicial": "inicial", "orcamento_atualizado": "atualizado",
    "orcamento_empenhado": "empenhado", "orcamento_realizado": "realizado",
}
_VALORES = ["inicial", "atualizado", "empenhado", "realizado"]
COLUNAS_SAIDA = [c for c in _COLUNAS.values()]


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """CSV cru do orçamento da despesa -> colunas padronizadas, valores numéricos (R$ nominais)."""
    slugs = {c: _slug(c) for c in df.columns}
    escolhidas = {}
    for original, slug in slugs.items():
        for prefixo, destino in _COLUNAS.items():
            if slug == prefixo or (destino in _VALORES and slug.startswith(prefixo)):
                escolhidas.setdefault(destino, original)
    faltam = [d for d in ("ano", "funcao", "grupo", "orgao_superior", "realizado") if d not in escolhidas]
    if faltam:
        raise ValueError(f"Colunas não encontradas: {faltam}. Colunas do arquivo: {list(df.columns)}")
    out = pd.DataFrame({destino: df[original] for destino, original in escolhidas.items()})
    for c in _VALORES:
        if c in out:
            out[c] = _numero(out[c].astype("string"))
    out["ano"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int64")
    for c in out.columns:
        if c not in _VALORES and c != "ano":
            out[c] = out[c].astype("string").str.strip()
    return out.dropna(subset=["ano", "realizado"]).reset_index(drop=True)


def anos(inicio: int = PRIMEIRO_ANO, fim: int | None = None) -> list[int]:
    return list(range(inicio, (fim or dt.date.today().year) + 1))


def baixar_todos(inicio: int = PRIMEIRO_ANO, fim: int | None = None, pasta: Path = DESTINO) -> list[Path]:
    hoje = dt.date.today().year
    caminhos, ignorados = [], []
    for ano in anos(inicio, fim):
        forcar = ano > hoje - ANOS_SEMPRE_ATUALIZADOS
        for tentativa in range(1, 4):
            try:
                caminhos.append(baixar_ano(ano, pasta, forcar=forcar))
                break
            except (requests.RequestException, ValueError) as e:
                if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code == 404:
                    print(f"{ano}: não publicado (404)")
                    ignorados.append(ano)
                    break
                print(f"{ano}: tentativa {tentativa}/3 falhou ({e})")
                if tentativa == 3:
                    ignorados.append(ano)
                else:
                    time.sleep(5 * 2 ** (tentativa - 1))
        time.sleep(1.0)
    print(f"Anos baixados/em cache: {len(caminhos)} | ignorados: {ignorados}")
    return caminhos


def consolidar(pasta: Path = DESTINO, saida: Path = SAIDA) -> pd.DataFrame:
    partes = []
    for zip_path in sorted(pasta.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            for nome in zf.namelist():
                if nome.lower().endswith(".csv"):
                    partes.append(normalizar(ler_csv(zf, nome)))
    if not partes:
        raise SystemExit("Nenhum arquivo para consolidar.")
    df = pd.concat(partes, ignore_index=True)
    saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(saida, index=False)
    print(f"{len(df):,} linhas, anos {int(df['ano'].min())}-{int(df['ano'].max())} -> {saida}")
    return df


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
    if "--tudo" in sys.argv:
        baixar_todos()
        consolidar()
    elif "--inspecionar" in sys.argv and args:
        inspecionar(int(args[0]))
    else:
        raise SystemExit("Uso: python -m pipeline.transparencia --inspecionar AAAA | --tudo")


if __name__ == "__main__":
    main()
