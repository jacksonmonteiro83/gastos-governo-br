"""Projeções de população do IBGE (SIDRA / API de agregados).

Por enquanto só inspeção: descobre qual tabela traz a população por idade (projeção) e quais
são seus períodos, variáveis e classificações, para depois escrevermos a ingestão certa.

    python -m pipeline.ibge --inspecionar
"""
import json
import sys

import requests

AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
CANDIDATAS = [7360, 9109, 9110, 6407]  # 6407: estimativas 2012-2025; 7360: indicadores da projeção; 9109/9110: projeção rev. 2024?


def _get(url: str, **params):
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def _tentar(titulo: str, fn) -> None:
    print(f"\n=== {titulo}")
    try:
        fn()
    except Exception as e:  # inspeção: nunca aborta no primeiro erro
        print(f"ERRO: {type(e).__name__}: {e}")


def listar_projecoes() -> None:
    """Lista toda tabela cuja pesquisa ou nome menciona projeção/idade/população."""
    dados = _get(AGREGADOS)
    for pesquisa in dados:
        pn = pesquisa.get("nome", "")
        for ag in pesquisa.get("agregados", []):
            nome = ag.get("nome", "")
            if "rojeç" in pn or "rojeç" in nome or ("idade" in nome.lower() and "popul" in nome.lower()):
                print(ag["id"], "|", pn, "|", nome)


def metadados(tabela: int) -> None:
    m = _get(f"{AGREGADOS}/{tabela}/metadados")
    print("nome:", m.get("nome"), "| periodicidade:", m.get("periodicidade"))
    print("variaveis:", [(v["id"], v["nome"]) for v in m.get("variaveis", [])])
    print("niveis:", m.get("nivelTerritorial"))
    for c in m.get("classificacoes", []):
        cats = c.get("categorias", [])
        print(f"classificacao {c['id']} '{c['nome']}': {len(cats)} categorias")
        for cat in (cats if len(cats) <= 40 else cats[:6] + cats[-3:]):
            print("   ", cat["id"], cat["nome"])
    per = _get(f"{AGREGADOS}/{tabela}/periodos")
    ids = [p["id"] for p in per]
    print("periodos:", len(ids), ids[:3], "...", ids[-3:])


def amostra(tabela: int) -> None:
    """Tenta uma consulta SIDRA bem aberta (Brasil, último período) para ver o formato."""
    url = f"https://apisidra.ibge.gov.br/values/t/{tabela}/n1/1/p/last/f/n"
    r = requests.get(url, timeout=60)
    print("GET", url, "->", r.status_code)
    print(r.text[:1200])


def inspecionar() -> None:
    _tentar("Agregados do assunto 'Projeção'", listar_projecoes)
    for t in CANDIDATAS:
        _tentar(f"Metadados da tabela {t}", lambda t=t: metadados(t))
        _tentar(f"Amostra SIDRA da tabela {t}", lambda t=t: amostra(t))


FTP = "https://ftp.ibge.gov.br/Projecao_da_Populacao/"


def listar_ftp(url: str = FTP, nivel: int = 0, maximo: int = 2) -> None:
    """Lista recursivamente (até `maximo` níveis) os arquivos publicados pelo IBGE."""
    import re

    r = requests.get(url, timeout=60)
    print(("  " * nivel) + url, "->", r.status_code)
    if r.status_code != 200:
        return
    for href in re.findall(r'href="([^"?][^"]*)"', r.text):
        if href.startswith("/") or href.startswith(".."):
            continue
        print(("  " * (nivel + 1)) + href)
        if href.endswith("/") and nivel < maximo:
            _tentar(url + href, lambda u=url + href: listar_ftp(u, nivel + 1, maximo))


BASE_2024 = FTP + "Projecao_da_Populacao_2024/"
ARQUIVOS_2024 = [
    "projecoes_2024_tab3_grupos_etarios_especificos.xlsx",
    "projecoes_2024_tab4_indicadores.xlsx",
    "projecoes_2024_tab2_grupo_quinquenal.xlsx",
]


def baixar_2024(nome: str):
    from pathlib import Path

    destino = Path("data/raw/ibge") / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        r = requests.get(BASE_2024 + nome, timeout=300)
        r.raise_for_status()
        destino.write_bytes(r.content)
    return destino


def inspecionar_xlsx() -> None:
    """Mostra abas, dimensões e as primeiras linhas de cada planilha da revisão 2024."""
    import pandas as pd

    for nome in ARQUIVOS_2024:
        def um(nome=nome):
            arq = baixar_2024(nome)
            xl = pd.ExcelFile(arq)
            print(nome, "| abas:", xl.sheet_names)
            for aba in xl.sheet_names[:3]:
                df = xl.parse(aba, header=None)
                print(f"--- aba '{aba}' {df.shape[0]}x{df.shape[1]}")
                with pd.option_context("display.width", 250, "display.max_columns", 14, "display.max_colwidth", 38):
                    print(df.head(14).iloc[:, :12].to_string())
                    print("   ...")
                    print(df.iloc[:, :6].tail(3).to_string())
        _tentar(nome, um)


if __name__ == "__main__":
    if "--xlsx" in sys.argv:
        inspecionar_xlsx()
    elif "--ftp" in sys.argv:
        _tentar("Arquivos de projeção no servidor do IBGE", listar_ftp)
    elif "--inspecionar" in sys.argv:
        inspecionar()
    else:
        print(__doc__)
