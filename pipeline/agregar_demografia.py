"""Envelhecimento da população brasileira: idosos para cada 100 pessoas em idade de trabalhar.

Entrada : projecoes_2024_tab2_grupo_quinquenal.xlsx (IBGE, Projeções da População, revisão 2024),
          baixada de ftp.ibge.gov.br para data/raw/ibge/
Saída   : docs/demografia_data.js  (window.DEMO = {...})

Brasil, ambos os sexos, 2000-2070. Grupos: jovens 0-14, idade ativa 15-64, idosos 65+.
Razão de dependência de idosos = pessoas de 65+ para cada 100 de 15-64.
Os anos a partir de `PRIMEIRO_ANO_PROJECAO` são projeção, não contagem.
"""
import json
from pathlib import Path

import pandas as pd

ARQUIVO = "projecoes_2024_tab2_grupo_quinquenal.xlsx"
PRIMEIRO_ANO_PROJECAO = 2025
SAIDA = Path("docs/demografia_data.js")


def _idade_inicial(rotulo: str) -> int:
    return int(str(rotulo).strip().replace("+", "-").split("-")[0])


def ler_quinquenal(bruto: pd.DataFrame) -> pd.DataFrame:
    """Planilha crua (header=None) -> tabela longa: ano, idade_inicial, populacao (Brasil, ambos os sexos)."""
    topo = bruto.index[bruto[0].astype(str).str.strip() == "GRUPO ETÁRIO"]
    if len(topo) == 0:
        raise ValueError("Cabeçalho 'GRUPO ETÁRIO' não encontrado na planilha.")
    i = topo[0]
    anos = {c: int(float(v)) for c, v in bruto.loc[i].items() if c >= 5 and pd.notna(v)}
    corpo = bruto.loc[i + 1:]
    corpo = corpo[(corpo[3].astype(str).str.strip() == "BR") & (corpo[1].astype(str).str.strip() == "Ambos")]
    corpo = corpo[corpo[0].astype(str).str.strip().str.match(r"^\d{2}(-\d{2}|\+)$")]  # ignora linhas de total/notas
    longo = corpo[[0, *anos]].rename(columns={0: "grupo", **anos}).melt(id_vars="grupo", var_name="ano", value_name="populacao")
    longo["idade_inicial"] = longo["grupo"].map(_idade_inicial)
    longo["populacao"] = pd.to_numeric(longo["populacao"], errors="coerce")
    return longo[["ano", "idade_inicial", "populacao"]].dropna()


def agregar(longo: pd.DataFrame) -> dict:
    ini = longo["idade_inicial"]
    faixa = pd.cut(ini, [-1, 14, 64, 200], labels=["jovens", "ativa", "idosos"])
    t = longo.assign(faixa=faixa).pivot_table(index="ano", columns="faixa", values="populacao", aggfunc="sum", observed=False)
    t["total"] = t.sum(axis=1)
    t["razao_idosos"] = 100 * t["idosos"] / t["ativa"]
    t["pct_idosos"] = 100 * t["idosos"] / t["total"]
    t = t.sort_index()
    anos = [int(a) for a in t.index]
    f = lambda c, n=1: [round(float(v), n) for v in t[c]]
    return {
        "anos": anos,
        "primeiro_ano_projecao": PRIMEIRO_ANO_PROJECAO,
        "razao_idosos": f("razao_idosos"),
        "pct_idosos": f("pct_idosos"),
        "idosos_mi": [round(float(v) / 1e6, 1) for v in t["idosos"]],
        "ativa_mi": [round(float(v) / 1e6, 1) for v in t["ativa"]],
        "pessoas_ativas_por_idoso": [round(float(a / i), 1) for a, i in zip(t["ativa"], t["idosos"])],
    }


def main() -> None:
    from pipeline.ibge import baixar_2024

    arq = baixar_2024(ARQUIVO)
    bruto = pd.read_excel(arq, header=None)
    dados = agregar(ler_quinquenal(bruto))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.DEMO = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    a = dados["anos"]
    print(f"{a[0]}-{a[-1]} -> {SAIDA} | razão 65+/15-64: {dados['razao_idosos'][0]} -> {dados['razao_idosos'][-1]}")


if __name__ == "__main__":
    main()
