"""Tesouro Transparente: Resultado do Tesouro Nacional (série mensal desde 1997).

O XLSX muda de nome todo mês (ex.: seriehistoricajul26.xlsx), mas o id do recurso
no CKAN é estável. Por isso resolvemos a URL atual pela API do CKAN.

Uso:
    python -m pipeline.tesouro               # baixa o XLSX e gera o Parquet normalizado
    python -m pipeline.tesouro --inspecionar # lista abas e primeiras linhas

Formato de saída (data/raw/tesouro_rtn_mensal.parquet), uma linha por tabela/linha/mês:
    tabela, base, referencia, data, ordem, codigo, nivel, descricao, rotulo_original, valor
- base: "corrente" (R$ milhões da época) ou "constante_ipca" (R$ milhões de `referencia`)
- ordem: posição da linha na aba (chave única junto com tabela e data)
- codigo/nivel: hierarquia extraída do rótulo (ex.: "4.2.1" -> nível 3); None em memorandos
"""
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd
import requests

from pipeline.config import RAW_DIR

CKAN_PACKAGE_SHOW = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
DATASET_ID = "ab56485b-9c40-4efb-8563-9ce3e1973c4b"
RESOURCE_ID = "527ccdb1-3059-42f3-bf23-b5e3ab4c6dc6"  # Série Histórica - Mensal (XLSX)
DESTINO = RAW_DIR / "tesouro_serie_historica.xlsx"
SAIDA = RAW_DIR / "tesouro_rtn_mensal.parquet"

# Abas mensais em formato "linhas = contas, colunas = meses".
# (1.2-B é acumulado em 12 meses e fica de fora de propósito.)
ABAS_MENSAIS = [
    "1.1", "1.1-A", "1.2", "1.2-A", "1.3", "1.3-A",
    "1.4", "1.4-A", "1.5", "1.5-A", "1.6",
]

_RE_NOTA = re.compile(r"\s*\d+/$")  # marcador de nota de rodapé no fim do rótulo ("... 13/")
_RE_CODIGO = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*(?:[-–]\s*)?(.*)$")
_RE_REFERENCIA = re.compile(r"Valores de (\w{3}/\d{4})")


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


def _eh_data(v) -> bool:
    return isinstance(v, (dt.datetime, dt.date, pd.Timestamp))


def limpar_rotulo(rotulo: str) -> tuple[str | None, int | None, str]:
    """Separa (codigo, nivel, descricao) de um rótulo como '4.2.1 Sent. Judiciais...'."""
    texto = re.sub(r"\s+", " ", str(rotulo)).strip()
    texto = _RE_NOTA.sub("", texto)
    m = _RE_CODIGO.match(texto)
    if m and m.group(2):
        codigo = m.group(1)
        return codigo, codigo.count(".") + 1, m.group(2).strip()
    return None, None, texto


def normalizar_aba(bruto: pd.DataFrame, aba: str) -> pd.DataFrame:
    """Converte uma aba mensal (lida com header=None) para formato longo."""
    # linha de cabeçalho = primeira linha com várias datas
    cabecalho = next(
        (i for i in range(min(15, len(bruto))) if bruto.iloc[i, 1:].map(_eh_data).sum() > 3),
        None,
    )
    if cabecalho is None:
        raise ValueError(f"Aba {aba}: não encontrei a linha de datas.")

    unidade = " ".join(str(v) for v in bruto.iloc[:cabecalho, 0].dropna())
    constante = "IPCA" in unidade
    ref = _RE_REFERENCIA.search(unidade)

    datas = bruto.iloc[cabecalho, 1:]
    datas = datas[datas.map(_eh_data)]
    posicoes = [bruto.columns.get_loc(c) for c in datas.index]
    valores = bruto.iloc[cabecalho + 1:, posicoes].copy()
    valores.columns = [pd.Timestamp(d).date() for d in datas.values]
    ids = pd.DataFrame({
        "ordem": range(cabecalho + 1, cabecalho + 1 + len(valores)),
        "rotulo_original": bruto.iloc[cabecalho + 1:, 0].to_numpy(),
    })
    corpo = pd.concat([ids, valores.reset_index(drop=True)], axis=1)
    corpo = corpo[corpo["rotulo_original"].notna()]

    longo = corpo.melt(
        id_vars=["ordem", "rotulo_original"], var_name="data", value_name="valor"
    )
    longo["valor"] = pd.to_numeric(longo["valor"], errors="coerce")
    longo = longo.dropna(subset=["valor"])  # remove notas de rodapé e linhas em branco

    partes = longo["rotulo_original"].map(limpar_rotulo)
    longo["codigo"] = partes.map(lambda p: p[0])
    longo["nivel"] = partes.map(lambda p: p[1]).astype("Int64")
    longo["descricao"] = partes.map(lambda p: p[2])
    longo["rotulo_original"] = longo["rotulo_original"].astype(str).str.strip()
    longo["tabela"] = aba
    longo["base"] = "constante_ipca" if constante else "corrente"
    longo["referencia"] = ref.group(1) if ref else None

    colunas = ["tabela", "base", "referencia", "data", "ordem", "codigo", "nivel",
               "descricao", "rotulo_original", "valor"]
    return longo[colunas].sort_values(["tabela", "ordem", "data"]).reset_index(drop=True)


def normalizar(caminho: Path = DESTINO) -> pd.DataFrame:
    xls = pd.ExcelFile(caminho)
    abas = [a for a in ABAS_MENSAIS if a in xls.sheet_names]
    faltando = set(ABAS_MENSAIS) - set(abas)
    if faltando:
        print(f"Aviso: abas ausentes no arquivo: {sorted(faltando)}")
    partes = [normalizar_aba(xls.parse(a, header=None), a) for a in abas]
    return pd.concat(partes, ignore_index=True)


def inspecionar(caminho: Path = DESTINO, linhas: int = 6) -> None:
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
        return
    baixar()
    df = normalizar()
    df.to_parquet(SAIDA, index=False)
    print(f"{len(df):,} linhas -> {SAIDA}")


if __name__ == "__main__":
    main()
