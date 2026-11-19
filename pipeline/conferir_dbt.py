"""Confere se os marts do dbt batem com os números que o pipeline Python publicou no painel.

Duas implementações independentes (SQL no dbt, pandas no pipeline) da mesma conta: se divergirem,
uma das duas está errada. Roda depois do `dbt build`; sai com código 1 se houver diferença.

    python -m pipeline.conferir_dbt              # previdência (RGPS)
    python -m pipeline.conferir_dbt --despesas   # despesas por ano e categoria
    python -m pipeline.conferir_dbt --emendas    # emendas por ano e tipo
"""
import json
import sys
from pathlib import Path


BANCO = Path("data/gastos.duckdb")
PREVIDENCIA_JS = Path("docs/previdencia_data.js")
DESPESAS_JS = Path("docs/despesas_data.js")
EMENDAS_JS = Path("docs/emendas_data.js")
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


def comparar_despesas(totais: list[tuple], categorias: list[tuple], painel: dict) -> list[str]:
    """totais: (ano, total_bi) do mart_despesas_anual; categorias: (ano, categoria, pct) do
    mart_despesas_categoria; painel: window.DESP. Os dois arredondam a 1 casa, então a tolerância é de arredondamento."""
    erros = []
    indice = {a: i for i, a in enumerate(painel["anos"])}
    for ano, total in totais:
        if ano not in indice:
            erros.append(f"{ano}: ano está no dbt e não no painel")
        elif abs(total - painel["total_bi"][indice[ano]]) > TOLERANCIA_BI:
            erros.append(f"{ano} total: dbt {total} x painel {painel['total_bi'][indice[ano]]}")
    for ano, cat, pct in categorias:
        if ano not in indice or cat not in painel["composicao"]:
            erros.append(f"{ano} {cat}: ausente no painel")
            continue
        js = painel["composicao"][cat][indice[ano]]
        if js is None or abs(pct - js) > TOLERANCIA_BI:
            erros.append(f"{ano} {cat}: dbt {pct}% x painel {js}%")
    return erros


def conferir_despesas() -> int:
    import duckdb

    con = duckdb.connect(str(BANCO), read_only=True)
    totais = con.execute("select ano, total_bi from mart_despesas_anual order by ano").fetchall()
    categorias = con.execute("select ano, categoria, pct from mart_despesas_categoria order by 1, 2").fetchall()
    erros = comparar_despesas(totais, categorias, carregar_js(DESPESAS_JS))
    if erros:
        print("Divergências entre dbt e painel (despesas):", *erros, sep="\n  ")
        return 1
    print(f"Despesas: {len(totais)} anos e {len(categorias)} categorias conferidos, dbt = painel "
          f"(tolerância {TOLERANCIA_BI}).")
    return 0


def comparar_emendas(totais: list[tuple], tipos: list[tuple], painel: dict) -> list[str]:
    """totais: (ano, total_bi, executado_pct) do mart_emendas_anual; tipos: (ano, tipo, bi) do mart_emendas_tipo_ano;
    painel: window.EMD. Os dois arredondam a 1 casa; a tolerância é de arredondamento."""
    erros = []
    indice = {a: i for i, a in enumerate(painel["anos"])}
    for ano, total, exec_pct in totais:
        if ano not in indice:
            erros.append(f"{ano}: ano está no dbt e não no painel")
            continue
        i = indice[ano]
        if abs(total - painel["total_bi"][i]) > TOLERANCIA_BI:
            erros.append(f"{ano} total: dbt {total} x painel {painel['total_bi'][i]}")
        js = painel["executado_pct"][i]
        if (exec_pct is None) != (js is None) or (js is not None and abs(exec_pct - js) > TOLERANCIA_BI):
            erros.append(f"{ano} executado: dbt {exec_pct}% x painel {js}%")
    for ano, tipo, bi in tipos:
        if ano not in indice or tipo not in painel["tipos"]:
            erros.append(f"{ano} {tipo}: ausente no painel")
        elif abs(bi - painel["tipos"][tipo][indice[ano]]) > TOLERANCIA_BI:
            erros.append(f"{ano} {tipo}: dbt {bi} x painel {painel['tipos'][tipo][indice[ano]]}")
    return erros


def conferir_emendas() -> int:
    import duckdb

    con = duckdb.connect(str(BANCO), read_only=True)
    totais = con.execute("select ano, total_bi, executado_pct from mart_emendas_anual order by ano").fetchall()
    tipos = con.execute("select ano, tipo, bi from mart_emendas_tipo_ano order by 1, 2").fetchall()
    erros = comparar_emendas(totais, tipos, carregar_js(EMENDAS_JS))
    if erros:
        print("Divergências entre dbt e painel (emendas):", *erros, sep="\n  ")
        return 1
    print(f"Emendas: {len(totais)} anos e {len(tipos)} combinações ano x tipo conferidos, dbt = painel "
          f"(tolerância {TOLERANCIA_BI}).")
    return 0


def main() -> int:
    if "--emendas" in sys.argv:
        return conferir_emendas()
    if "--despesas" in sys.argv:
        return conferir_despesas()
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
