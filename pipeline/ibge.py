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


if __name__ == "__main__":
    if "--inspecionar" in sys.argv:
        inspecionar()
    else:
        print(__doc__)
