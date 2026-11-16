"""Agrega a previdência do INSS (RGPS) em totais anuais para o painel (docs/previdencia_data.js).

Entrada : data/raw/tesouro_rtn_mensal.parquet (pipeline.tesouro) e, opcionalmente,
          data/raw/bcb_pib_12m.parquet (PIB acumulado em 12 meses, R$ milhões, SGS 4382)
Saída   : docs/previdencia_data.js  (window.PREV = {...})

Arrecadação líquida para o RGPS (linha 1.3) e benefícios previdenciários (linha 4.1) vêm da
mesma tabela do Resultado do Tesouro Nacional. Valores constantes (IPCA) na tabela 1.2-A; os
percentuais do PIB usam a tabela 1.2 em valores correntes, divididos pelo PIB de dezembro.
Necessidade de financiamento = benefícios - arrecadação líquida (positivo = o Tesouro cobre a diferença).
"""
import json
import sys
from pathlib import Path

import pandas as pd

ENTRADA = Path("data/raw/tesouro_rtn_mensal.parquet")
PIB = Path("data/raw/bcb_pib_12m.parquet")
SAIDA = Path("docs/previdencia_data.js")
TAB_REAL, TAB_CORRENTE = "1.2-A", "1.2"


def _linha(t: pd.DataFrame, codigo: str, palavras: list[str]) -> pd.Series:
    """Série mensal (R$ milhões) da linha de código `codigo` cuja descrição traz as `palavras`."""
    desc = t["descricao"].fillna("").str.upper()
    ok = t["codigo"].eq(codigo)
    for p in palavras:
        ok &= desc.str.contains(p, regex=False)
    sel = t[ok]
    if sel.empty:  # código mudou? tenta só pela descrição
        ok = pd.Series(True, index=t.index)
        for p in palavras:
            ok &= desc.str.contains(p, regex=False)
        sel = t[ok]
    if sel.empty:
        raise ValueError(f"Linha {codigo} {palavras} não encontrada na tabela.")
    return sel.groupby("data")["valor"].sum()


def _mensais(df: pd.DataFrame, tabela: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    t = df[df["tabela"] == tabela].copy()
    t["data"] = pd.to_datetime(t["data"])
    arrec = _linha(t, "1.3", ["RGPS"])
    benef = _linha(t, "4.1", ["BENEF"])
    desp = t[(t["codigo"] == "4") & (t["nivel"] == 1)].set_index("data")["valor"]
    return arrec, benef, desp


def _num(v, casas=2):
    return None if pd.isna(v) else round(float(v), casas)


def agregar(df: pd.DataFrame, pib: pd.DataFrame | None = None) -> dict:
    arrec, benef, desp = _mensais(df, TAB_REAL)
    ultimo = min(arrec.index.max(), benef.index.max(), desp.index.max())
    arrec, benef, desp = (s[s.index <= ultimo] for s in (arrec, benef, desp))
    ano = lambda s: s.groupby(s.index.year).sum() / 1e3  # R$ bi
    A, B, D = ano(arrec), ano(benef), ano(desp)
    meses = arrec.groupby(arrec.index.year).size()
    anos = [int(y) for y in A.index]
    saldo = B - A

    # % do PIB: valores correntes / PIB acumulado em 12 meses de dezembro
    pib_ano = None
    if pib is not None and len(pib):
        p = pib.copy()
        p["data"] = pd.to_datetime(p["data"])
        dez = p[p["data"].dt.month == 12]
        pib_ano = pd.Series(dez["valor"].to_numpy(), index=dez["data"].dt.year.to_numpy())
    pct_pib_saldo, pct_pib_benef = [], []
    ac, bc, _ = _mensais(df, TAB_CORRENTE)
    Ac, Bc = ac.groupby(ac.index.year).sum(), bc.groupby(bc.index.year).sum()
    for y in anos:
        if pib_ano is not None and y in pib_ano.index and y in Ac.index and meses[y] == 12:
            pct_pib_saldo.append(_num(100 * (Bc[y] - Ac[y]) / pib_ano[y], 2))
            pct_pib_benef.append(_num(100 * Bc[y] / pib_ano[y], 2))
        else:
            pct_pib_saldo.append(None)
            pct_pib_benef.append(None)

    completos = [int(y) for y in meses.index if meses[y] == 12]
    ref = completos[-1]
    ref_i = anos.index(ref)
    return {
        "referencia": df.loc[df["tabela"] == TAB_REAL, "referencia"].dropna().iloc[0],
        "ultimo_mes": ultimo.strftime("%Y-%m"),
        "anos": anos,
        "meses": [int(meses[y]) for y in A.index],
        "arrecadacao": [_num(v) for v in A],
        "beneficios": [_num(v) for v in B],
        "necessidade": [_num(v) for v in saldo],
        "cobertura_pct": [_num(100 * a / b, 1) for a, b in zip(A, B)],
        "beneficios_pct_despesa_primaria": [_num(100 * b / d, 1) for b, d in zip(B, D)],
        "pct_pib_necessidade": pct_pib_saldo,
        "pct_pib_beneficios": pct_pib_benef,
        "destaques": {
            "ano_referencia": ref,
            "arrecadacao_bi": _num(A[ref], 1),
            "beneficios_bi": _num(B[ref], 1),
            "necessidade_bi": _num(saldo[ref], 1),
            "necessidade_por_dia_bi": _num(saldo[ref] / 365, 2),
            "cobertura_pct": _num(100 * A[ref] / B[ref], 1),
            "beneficios_pct_despesa_primaria": _num(100 * B[ref] / D[ref], 1),
            "pct_pib_necessidade": pct_pib_saldo[ref_i],
            "beneficios_crescimento_real_desde_2010_pct": (
                _num(100 * (B[ref] / B[2010] - 1), 0) if 2010 in B.index else None),
            "arrecadacao_crescimento_real_desde_2010_pct": (
                _num(100 * (A[ref] / A[2010] - 1), 0) if 2010 in A.index else None),
        },
    }


def main() -> None:
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    df = pd.read_csv(entrada) if entrada.suffix == ".csv" else pd.read_parquet(entrada)
    pib = pd.read_parquet(PIB) if PIB.exists() else None
    dados = agregar(df, pib)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.PREV = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(dados['anos'])} anos -> {SAIDA}")


if __name__ == "__main__":
    main()
