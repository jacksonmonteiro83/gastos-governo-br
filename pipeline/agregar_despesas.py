"""Agrega o orçamento da despesa federal (Portal da Transparência) para o painel docs/despesas_data.js.

Entrada : data/raw/orcamento_despesa.parquet (pipeline.transparencia) e data/raw/bcb_ipca_mensal.parquet
Saída   : docs/despesas_data.js  (window.DESP = {...})

Valor usado: "realizado" (despesa realizada no ano), em R$ bilhões de hoje (IPCA, fator médio do ano).
Amortização/refinanciamento da dívida (grupo 6) e reserva de contingência (grupo 9) ficam FORA dos
totais por função e por órgão: a amortização é rolagem de títulos e dominaria tudo (trilhões). Ela é
informada à parte nos destaques. Os juros (grupo 2) ficam dentro.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline.agregar_cpgf import fator_ipca

ENTRADA = Path("data/raw/orcamento_despesa.parquet")
IPCA = Path("data/raw/bcb_ipca_mensal.parquet")
SAIDA = Path("docs/despesas_data.js")
GRUPOS_FORA = {"6", "9"}   # amortização/refinanciamento da dívida; reserva de contingência
N_FUNCOES = 7              # + "Outras" = 8 categorias (limite da paleta categórica)
# Composição sem sobreposição: cada linha do orçamento entra na PRIMEIRA categoria que a descreve.
CATEGORIAS = ["Previdência social", "Pessoal e encargos", "Juros da dívida",
              "Saúde, educação e assistência", "Investimentos", "Outras"]
ORDEM_GRUPOS = ["Pessoal e Encargos Sociais", "Outras Despesas Correntes", "Juros e Encargos da Dívida",
                "Investimentos", "Inversões Financeiras"]


def _num(v, casas=1):
    return None if pd.isna(v) else round(float(v), casas)


def fator_anual(ipca: pd.DataFrame | None, anos: list[int]) -> pd.Series:
    """Fator médio do ano para trazer valores nominais ao último mês do IPCA (1.0 se não houver IPCA)."""
    if ipca is None or ipca.empty:
        return pd.Series(1.0, index=anos)
    f = fator_ipca(ipca)
    por_ano = f.groupby(f.index.year).mean()
    return pd.Series({a: float(por_ano.get(a, 1.0)) for a in anos})


def categoria(funcao: str, grupo: str) -> str:
    """Previdência (função, inclusive inativos) > juros > pessoal (demais funções) > saúde/educação/assistência
    (custeio e transferências) > investimentos > outras."""
    f, g = str(funcao).lower(), str(grupo)
    if "previd" in f:
        return "Previdência social"
    if g == "Juros e Encargos da Dívida":
        return "Juros da dívida"
    if g == "Pessoal e Encargos Sociais":
        return "Pessoal e encargos"
    if any(k in f for k in ("saúde", "educa", "assist")):
        return "Saúde, educação e assistência"
    if g == "Investimentos":
        return "Investimentos"
    return "Outras"


def agregar(df: pd.DataFrame, ipca: pd.DataFrame | None = None, ano_corrente: int | None = None) -> dict:
    ano_corrente = ano_corrente or dt.date.today().year
    d = df.copy()
    d["ano"] = d["ano"].astype(int)
    anos = sorted(d["ano"].unique().tolist())
    fatores = fator_anual(ipca, anos)
    d["real_bi"] = d["realizado"] * d["ano"].map(fatores) / 1e9
    d["atual_bi"] = d["atualizado"] * d["ano"].map(fatores) / 1e9
    dentro = d[~d["grupo_cod"].astype(str).isin(GRUPOS_FORA)]
    amort = d[d["grupo_cod"].astype(str) == "6"]

    por_ano = lambda x: x.groupby("ano")["real_bi"].sum().reindex(anos, fill_value=0.0)
    total = por_ano(dentro)

    # funções: as N maiores no acumulado + "Outras" (ordem fixa = ordem do acumulado)
    acum = dentro.groupby("funcao")["real_bi"].sum().sort_values(ascending=False)
    top = list(acum.index[:N_FUNCOES])
    funcoes = {f: [_num(v) for v in por_ano(dentro[dentro["funcao"] == f])] for f in top}
    outras = total - sum(por_ano(dentro[dentro["funcao"] == f]) for f in top)
    if len(acum) > N_FUNCOES:
        funcoes["Outras"] = [_num(v) for v in outras]

    grupos = {g: [_num(v) for v in por_ano(dentro[dentro["grupo"] == g])] for g in ORDEM_GRUPOS
              if (dentro["grupo"] == g).any()}

    completos = [a for a in anos if a < ano_corrente]
    ref = completos[-1] if completos else anos[-1]
    ref_df = dentro[dentro["ano"] == ref]
    orgaos = (ref_df.groupby("orgao_superior")["real_bi"].sum().sort_values(ascending=False).head(12))
    pct = lambda x: _num(100 * x / total[ref])
    soma_f = lambda nome: ref_df[ref_df["funcao"].str.lower().str.contains(nome, regex=False)]["real_bi"].sum()
    grp = lambda g: ref_df[ref_df["grupo"] == g]["real_bi"].sum()
    atual = dentro[dentro["ano"] == ref]["atual_bi"].sum()
    dentro = dentro.assign(cat=[categoria(f, g) for f, g in zip(dentro["funcao"], dentro["grupo"])])
    cat_bi = {c: por_ano(dentro[dentro["cat"] == c]) for c in CATEGORIAS}
    composicao = {c: [_num(100 * v / t) if t else None for v, t in zip(cat_bi[c], total)] for c in CATEGORIAS}
    trio = ["Previdência social", "Pessoal e encargos", "Juros da dívida"]
    return {
        "anos": anos,
        "composicao": composicao,
        "composicao_ref_bi": {c: _num(cat_bi[c][ref]) for c in CATEGORIAS},
        "ano_corrente_parcial": ano_corrente in anos,
        "funcoes": funcoes,
        "grupos": grupos,
        "total_bi": [_num(v) for v in total],
        "orgaos_ano_ref": [{"orgao": o, "bi": _num(v), "pct": pct(v)} for o, v in orgaos.items()],
        "destaques": {
            "ano_referencia": int(ref),
            "total_bi": _num(total[ref]),
            "amortizacao_bi": _num(por_ano(amort)[ref]),
            "previdencia_pct": pct(soma_f("previd")),
            "saude_pct": pct(soma_f("saúde")),
            "educacao_pct": pct(soma_f("educa")),
            "pessoal_pct": pct(grp("Pessoal e Encargos Sociais")),
            "juros_pct": pct(grp("Juros e Encargos da Dívida")),
            "investimentos_pct": pct(grp("Investimentos")),
            "execucao_pct": _num(100 * total[ref] / atual) if atual else None,
            "trio_pct": _num(sum(cat_bi[c][ref] for c in trio) * 100 / total[ref]),
            "trio_bi": _num(sum(cat_bi[c][ref] for c in trio)),
            "trio_dia_bi": _num(sum(cat_bi[c][ref] for c in trio) / 365, 2),
        },
    }


def main() -> None:
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    df = pd.read_parquet(entrada)
    ipca = pd.read_parquet(IPCA) if IPCA.exists() else None
    dados = agregar(df, ipca)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.DESP = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    a = dados["anos"]
    print(f"{a[0]}-{a[-1]} -> {SAIDA} | total {dados['destaques']['ano_referencia']}: R$ {dados['destaques']['total_bi']} bi")


if __name__ == "__main__":
    main()
