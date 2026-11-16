"""Projeções de população do IBGE (SIDRA / API de agregados).

Por enquanto só inspeção: descobre qual tabela traz a população por idade (projeção) e quais
são seus períodos, variáveis e classificações, para depois escrevermos a ingestão certa.

    python -m pipeline.ibge --inspecionar
"""
import json
import sys

import requests

AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
CANDIDATAS = [7358, 6407, 1209]  # 7358: projeções (rev. 2024)? 1209: população por idade (censos)


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
    dados = _get(AGREGADOS, assunto="Projeção")  # filtra por assunto; se não houver, lista tudo
    achou = False
    for pesquisa in dados:
        for ag in pesquisa.get("agregados", []):
            nome = ag.get("nome", "")
            if "rojeç" in nome or "rojec" in nome:
                achou = True
                print(ag["id"], "|", pesquisa.get("nome"), "|", nome)
    if not achou:
        print("nenhum agregado com 'Projeção' no nome; resposta crua (início):")
        print(json.dumps(dados, ensure_ascii=False)[:1500])


def metadados(tabela: int) -> None:
    m = _get(f"{AGREGADOS}/{tabela}/metadados")
    print("nome:", m.get("nome"), "| periodicidade:", m.get("periodicidade"))
    print("variaveis:", [(v["id"], v["nome"]) for v in m.get("variaveis", [])])
    print("niveis:", m.get("nivelTerritorial"))
    for c in m.get("classificacoes", []):
        cats = c.get("categorias", [])
        print(f"classificacao {c['id']} '{c['nome']}': {len(cats)} categorias")
        for cat in cats[:6] + (cats[-3:] if len(cats) > 9 else []):
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
