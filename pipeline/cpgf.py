"""Portal da Transparência: Cartão de Pagamento do Governo Federal (CPGF), dados mensais.

Uso:
    python -m pipeline.cpgf 202401               # baixa um mês (AAAAMM)
    python -m pipeline.cpgf --inspecionar 202401 # baixa e mostra arquivos, colunas e amostra
    python -m pipeline.cpgf --tudo               # baixa 2013 até hoje e gera o Parquet normalizado

O padrão de URL por mês (`.../download-de-dados/cpgf/AAAAMM`) foi confirmado com 202401:
um ZIP com `AAAAMM_CPGF.csv` (separador ;, latin-1, 15 colunas).

Privacidade: o CSV traz CPF mascarado e nome de cada portador (servidor) e, em parte das
linhas, pessoas físicas como favorecidas. A saída normalizada NÃO guarda portador nem nome
de pessoa física: só órgão, unidade gestora, tipo de transação e favorecidos pessoa jurídica.
"""
import datetime as dt
import io
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

URL_BASE = "https://portaldatransparencia.gov.br/download-de-dados/cpgf/"
DESTINO = RAW_DIR / "cpgf"
SAIDA = RAW_DIR / "cpgf_normalizado.parquet"
PRIMEIRO_MES = (2013, 1)
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


# ---------- normalização ----------
def _slug(coluna: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", coluna).encode("ascii", "ignore").decode()
    return re.sub(r"\W+", "_", sem_acento.strip().lower()).strip("_")


COLUNAS_SAIDA = [
    "ano_extrato", "mes_extrato", "orgao_superior_cod", "orgao_superior", "orgao_cod", "orgao",
    "ug_cod", "ug", "data_transacao", "tipo_transacao", "transacao", "sigiloso",
    "favorecido_tipo", "favorecido_cnpj", "favorecido_nome", "valor",
]
_RENOMEAR = {
    "codigo_orgao_superior": "orgao_superior_cod", "nome_orgao_superior": "orgao_superior",
    "codigo_orgao": "orgao_cod", "nome_orgao": "orgao",
    "codigo_unidade_gestora": "ug_cod", "nome_unidade_gestora": "ug",
    "cnpj_ou_cpf_favorecido": "favorecido_doc", "nome_favorecido": "favorecido_nome",
}


def _tipo_transacao(t: str) -> str:
    t = str(t).upper()
    if "SIGILO" in t:
        return "sigilo"
    if "SAQUE" in t:
        return "saque"
    if "COMPRA" in t:
        return "compra"
    return "outro"


def normalizar_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza um mês do CPGF. Remove portador e dados de pessoa física (privacidade)."""
    df = df.rename(columns=_slug).rename(columns=_RENOMEAR)
    obrigatorias = {"valor_transacao", "transacao", "data_transacao", "favorecido_doc",
                    "favorecido_nome", "orgao_superior", "ug"}
    faltam = obrigatorias - set(df.columns)
    if faltam:
        raise ValueError(f"Colunas ausentes no CSV do CPGF: {sorted(faltam)}")

    out = pd.DataFrame(index=df.index)
    for c in ("ano_extrato", "mes_extrato"):
        out[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ("orgao_superior_cod", "orgao_superior", "orgao_cod", "orgao", "ug_cod", "ug"):
        out[c] = df[c].str.strip()
    out["data_transacao"] = pd.to_datetime(df["data_transacao"], format="%d/%m/%Y", errors="coerce").dt.date
    out["transacao"] = df["transacao"].str.strip()
    out["tipo_transacao"] = df["transacao"].map(_tipo_transacao)
    out["sigiloso"] = out["tipo_transacao"].eq("sigilo")

    doc = df["favorecido_doc"].fillna("").str.strip()
    pj = doc.str.fullmatch(r"\d{14}")
    pf = doc.str.contains(r"\*", regex=True)
    nome = df["favorecido_nome"].str.strip()
    mei = pj & nome.str.contains(r"\s\d{11}$", regex=True, na=False)  # MEI: nome + CPF do titular
    out["favorecido_tipo"] = (pd.Series("sem_informacao", index=df.index)
                              .mask(pj, "pj").mask(mei, "mei").mask(pf, "pf"))
    empresa = pj & ~mei
    out["favorecido_cnpj"] = doc.where(empresa)
    out["favorecido_nome"] = nome.where(empresa)  # só empresas; pessoa física e MEI ficam anônimos
    valor = df["valor_transacao"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    out["valor"] = pd.to_numeric(valor, errors="coerce")
    return out[COLUNAS_SAIDA]


def ler_zip(caminho: Path) -> pd.DataFrame:
    with zipfile.ZipFile(caminho) as zf:
        nomes = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        return normalizar_mes(ler_csv(zf, nomes[0]))


def meses(inicio=PRIMEIRO_MES, fim=None):
    hoje = dt.date.today()
    ano, mes = inicio
    fim = fim or (hoje.year, hoje.month)
    while (ano, mes) <= fim:
        yield ano, mes
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def baixar_intervalo(inicio=PRIMEIRO_MES, fim=None, pasta: Path = DESTINO) -> list[Path]:
    """Baixa os meses ainda ausentes. Meses não publicados (404/não-ZIP) são ignorados."""
    caminhos = []
    for ano, mes in meses(inicio, fim):
        destino = pasta / f"{ano}{mes:02d}.zip"
        if not destino.exists():
            try:
                baixar_mes(ano, mes, pasta)
            except (requests.HTTPError, ValueError) as e:
                print(f"{ano}{mes:02d}: ignorado ({e})")
                destino.unlink(missing_ok=True)
                continue
            time.sleep(0.5)  # gentileza com o portal
        caminhos.append(destino)
    return caminhos


def consolidar(pasta: Path = DESTINO, saida: Path = SAIDA) -> pd.DataFrame:
    partes = [ler_zip(z) for z in sorted(pasta.glob("*.zip"))]
    df = pd.concat(partes, ignore_index=True)
    saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(saida, index=False)
    print(f"{len(df):,} linhas de {len(partes)} meses -> {saida}")
    return df


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
    if "--tudo" in sys.argv:
        baixar_intervalo()
        consolidar()
        return
    if not args:
        raise SystemExit("Uso: python -m pipeline.cpgf [--inspecionar] AAAAMM | --tudo")
    ano, mes = int(args[0][:4]), int(args[0][4:])
    if "--inspecionar" in sys.argv:
        inspecionar(ano, mes)
    else:
        baixar_mes(ano, mes)


if __name__ == "__main__":
    main()
