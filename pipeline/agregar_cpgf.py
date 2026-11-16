"""Agrega o CPGF normalizado em totais para o dashboard (docs/cpgf_data.js).

Entrada : data/raw/cpgf_normalizado.parquet (pipeline.cpgf) e data/raw/bcb_ipca_mensal.parquet
Saída   : docs/cpgf_data.js  (window.CPGF = {...})

Valores corrigidos pelo IPCA para o último mês disponível, usando o mês do extrato como
data de referência (as linhas sob sigilo não têm data de transação). Sem dado de pessoa física.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ENTRADA = Path("data/raw/cpgf_normalizado.parquet")
IPCA = Path("data/raw/bcb_ipca_mensal.parquet")
SAIDA = Path("docs/cpgf_data.js")
TOP = 10


def fator_ipca(ipca: pd.DataFrame) -> pd.Series:
    """Fator para trazer cada mês (Period M) ao valor do último mês da série do IPCA."""
    s = ipca.copy()
    s["data"] = pd.to_datetime(s["data"])
    s = s.sort_values("data")
    indice = (1 + s["valor"] / 100).cumprod()
    indice.index = s["data"].dt.to_period("M")
    return indice.iloc[-1] / indice


def _num(v, casas=2):
    return None if pd.isna(v) else round(float(v), casas)


def agregar(df: pd.DataFrame, ipca: pd.DataFrame) -> dict:
    d = df.dropna(subset=["ano_extrato", "mes_extrato", "valor"]).copy()
    d["periodo"] = pd.to_datetime({"year": d["ano_extrato"].astype(int),
                                   "month": d["mes_extrato"].astype(int), "day": 1}).dt.to_period("M")
    fatores = fator_ipca(ipca)
    d["real"] = d["valor"] * d["periodo"].map(fatores).fillna(1.0)  # meses além do IPCA: fator 1
    d["ano"] = d["ano_extrato"].astype(int)

    por_tipo = d.pivot_table(index="ano", columns="tipo_transacao", values="real", aggfunc="sum").fillna(0)
    for c in ("compra", "saque", "sigilo", "outro"):
        if c not in por_tipo:
            por_tipo[c] = 0.0
    meses = d.groupby("ano")["mes_extrato"].nunique()
    anos = [int(a) for a in por_tipo.index]
    total_ano = por_tipo[["compra", "saque", "sigilo", "outro"]].sum(axis=1)

    completos = [int(a) for a in anos if meses[a] == 12]
    ano_ref = completos[-1] if completos else anos[-1]
    total = d["real"].sum()

    orgaos = (d.groupby("orgao_superior")["real"].sum().sort_values(ascending=False).head(TOP))
    empresas = (d[d["favorecido_tipo"] == "pj"]
                .groupby(["favorecido_cnpj", "favorecido_nome"])["real"].agg(["sum", "count"])
                .sort_values("sum", ascending=False).head(TOP))

    ref = d.loc[d["ano"] == ano_ref]
    return {
        "ultimo_mes": str(d["periodo"].max()),
        "primeiro_mes": str(d["periodo"].min()),
        "anos": anos,
        "meses": [int(meses[a]) for a in anos],
        "compra": [_num(por_tipo.loc[a, "compra"] + por_tipo.loc[a, "outro"] , 0) for a in anos],
        "saque": [_num(por_tipo.loc[a, "saque"], 0) for a in anos],
        "sigilo": [_num(por_tipo.loc[a, "sigilo"], 0) for a in anos],
        "transacoes": [int((d["ano"] == a).sum()) for a in anos],
        "orgaos": [{"nome": n, "valor": _num(v, 0)} for n, v in orgaos.items()],
        "empresas": [{"nome": n, "cnpj": c, "valor": _num(r["sum"], 0), "transacoes": int(r["count"])}
                     for (c, n), r in empresas.iterrows()],
        "destaques": {
            "total_real": _num(total, 0),
            "sigilo_pct": _num(100 * d.loc[d["tipo_transacao"] == "sigilo", "real"].sum() / total, 1),
            "saque_pct": _num(100 * d.loc[d["tipo_transacao"] == "saque", "real"].sum() / total, 1),
            "ano_referencia": ano_ref,
            "ano_ref_total": _num(ref["real"].sum(), 0),
            "ano_ref_sigilo_pct": _num(100 * ref.loc[ref["tipo_transacao"] == "sigilo", "real"].sum() / ref["real"].sum(), 1),
            "ano_ref_saque_pct": _num(100 * ref.loc[ref["tipo_transacao"] == "saque", "real"].sum() / ref["real"].sum(), 1),
            "transacoes_total": int(len(d)),
        },
    }


def main() -> None:
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    df = pd.read_csv(entrada) if entrada.suffix == ".csv" else pd.read_parquet(entrada)
    ipca = pd.read_parquet(IPCA) if IPCA.suffix == ".parquet" else pd.read_csv(IPCA)
    dados = agregar(df, ipca)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.CPGF = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(dados['anos'])} anos -> {SAIDA}")


if __name__ == "__main__":
    main()
