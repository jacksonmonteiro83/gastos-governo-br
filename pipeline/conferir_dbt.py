"""Confere se os marts do dbt batem com os números que o pipeline Python publicou no painel.

Duas implementações independentes (SQL no dbt, pandas no pipeline) da mesma conta: se divergirem,
uma das duas está errada. Roda depois do `dbt build`; sai com código 1 se houver diferença.

    python -m pipeline.conferir_dbt
"""
import json
import sys
from pathlib import Path


BANCO = Path("data/gastos.duckdb")
PREVIDENCIA_JS = Path("docs/previdencia_data.js")
TOLERANCIA_BI = 0.11  # o painel arredonda para 2 casas por série; a diferença é arredondamento


def carregar_js(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8")
    return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])


def comparar_rgps(linhas: list[tuple], painel: dict) -> list[str]:
    """linhas: (ano, arrecadacao_bi, beneficios_bi, necessidade_bi) do mart; painel: window.PREV."""
    erros = []
    indice = {a: i for i, a in enumerate(painel["anos"])}
    for ano, arrec, benef, nec in linhas:
        if ano not in indice:
            erros.append(f"{ano}: ano está no dbt e não no painel")
            continue
        i = indice[ano]
        for nome, dbt_v, js_v in (("arrecadacao", arrec, painel["arrecadacao"][i]),
                                  ("beneficios", benef, painel["beneficios"][i]),
                                  ("necessidade", nec, painel["necessidade"][i])):
            if abs(dbt_v - js_v) > TOLERANCIA_BI:
                erros.append(f"{ano} {nome}: dbt {dbt_v} x painel {js_v}")
    return erros


def main() -> int:
    import duckdb  # só aqui: os testes de `comparar_rgps` não precisam do DuckDB

    con = duckdb.connect(str(BANCO), read_only=True)
    linhas = con.execute(
        "select ano, arrecadacao_bi, beneficios_bi, necessidade_bi from mart_rgps_anual "
        "where ano_completo order by ano").fetchall()
    erros = comparar_rgps(linhas, carregar_js(PREVIDENCIA_JS))
    if erros:
        print("Divergências entre dbt e painel:", *erros, sep="\n  ")
        return 1
    print(f"RGPS: {len(linhas)} anos completos conferidos, dbt = painel (tolerância R$ {TOLERANCIA_BI} bi).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
