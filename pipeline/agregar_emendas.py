"""Agrega as emendas parlamentares (Portal da Transparência) para o painel docs/emendas_data.js.

Entrada : data/raw/emendas.parquet (pipeline.emendas) e data/raw/bcb_ipca_mensal.parquet
Saída   : docs/emendas_data.js  (window.EMD = {...})

Valor principal: EMPENHADO (dinheiro reservado para a emenda no ano), em R$ bilhões de hoje (IPCA, fator
médio do ano da emenda). "Executado" = pago no ano + restos a pagar pagos depois, sobre o empenhado: anos
recentes ainda estão em execução, então a taxa deles sobe com o tempo. O autor só existe para parte das
emendas (as de relator e antigas aparecem sem autor); isso é informado, não escondido.
"""
import datetime as dt
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from pipeline.agregar_despesas import fator_anual

ENTRADA = Path("data/raw/emendas.parquet")
POPULACAO = Path("data/raw/populacao_uf.parquet")
IPCA = Path("data/raw/bcb_ipca_mensal.parquet")
SAIDA = Path("docs/emendas_data.js")
SEM_AUTOR = {"", "sem informacao", "sem informação", "s/i"}
TIPOS = {  # nome no arquivo -> rótulo curto (ordem fixa = ordem das cores)
    "Emenda Individual - Transferências com Finalidade Definida": "Individual (finalidade definida)",
    "Emenda Individual - Transferências Especiais": "Individual (transferência especial)",
    "Emenda de Bancada": "Bancada",
    "Emenda de Comissão": "Comissão",
    "Emenda de Relator": "Relator",
}
REGIOES_UF = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}


def _num(v, casas=1):
    return None if pd.isna(v) else round(float(v), casas)


def _top(s: pd.Series, n: int = 10) -> list[dict]:
    s = s.sort_values(ascending=False)
    total = s.sum()
    if not total:
        return []
    return [{"nome": str(k), "bi": _num(v, 2), "pct": _num(100 * v / total)} for k, v in s.head(n).items()]


def _chave(nome: str) -> str:
    """'SÃO PAULO' e 'São Paulo' viram a mesma chave."""
    t = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode().lower()
    return " ".join(t.split())


def por_habitante(emendas_uf: pd.Series, pop: pd.DataFrame | None, ano: int) -> tuple[list[dict], int | None]:
    """emendas_uf: R$ bi por UF (nome) no ano. Devolve as UFs ordenadas por R$ por habitante e o ano da população
    usado (o mais recente disponível até `ano`). Sem população, devolve lista vazia."""
    if pop is None or pop.empty:
        return [], None
    anos_ok = [a for a in pop["ano"].unique() if a <= ano]
    if not anos_ok:
        return [], None
    ano_pop = int(max(anos_ok))
    atual = pop[pop["ano"] == ano_pop].assign(chave=lambda x: x["uf"].map(_chave)).set_index("chave")
    p, nomes = atual["populacao"], atual["uf"]   # nome com a grafia do IBGE ("Mato Grosso do Sul")
    linhas = []
    for nome, bi in emendas_uf.items():
        k = _chave(nome)
        if k in p.index and p[k] > 0:
            linhas.append({"nome": str(nomes[k]), "bi": _num(bi, 2),
                           "pop_mi": _num(p[k] / 1e6, 2), "reais_hab": _num(bi * 1e9 / p[k], 0)})
    return sorted(linhas, key=lambda x: -x["reais_hab"]), ano_pop


def agregar(df: pd.DataFrame, ipca: pd.DataFrame | None = None, ano_corrente: int | None = None,
            pop: pd.DataFrame | None = None) -> dict:
    ano_corrente = ano_corrente or dt.date.today().year
    d = df.copy()
    d["ano"] = d["ano"].astype(int)
    anos = sorted(d["ano"].unique().tolist())
    fatores = d["ano"].map(fator_anual(ipca, anos))
    for c in ("empenhado", "pago", "rap_pago"):
        d[c + "_bi"] = d.get(c, 0).fillna(0) * fatores / 1e9
    d["tipo_curto"] = d["tipo"].map(TIPOS).fillna(d["tipo"])
    nomes_tipos = [t for t in TIPOS.values() if (d["tipo_curto"] == t).any()]
    d["autor_ok"] = ~d["autor"].fillna("").str.lower().str.strip().isin(SEM_AUTOR)

    por_ano = lambda x, col="empenhado_bi": x.groupby("ano")[col].sum().reindex(anos, fill_value=0.0)
    total = por_ano(d)
    tipos = {t: [_num(v) for v in por_ano(d[d["tipo_curto"] == t])] for t in nomes_tipos}
    executado = ((por_ano(d, "pago_bi") + por_ano(d, "rap_pago_bi")) / total.replace(0, pd.NA) * 100)
    autor_ok = por_ano(d[d["autor_ok"]]) / total.replace(0, pd.NA) * 100

    completos = [a for a in anos if a < ano_corrente]
    ref = completos[-1] if completos else anos[-1]
    r = d[d["ano"] == ref]
    tot_ref = total[ref]
    pct = lambda x: _num(100 * x / tot_ref) if tot_ref else None
    rel = por_ano(d[d["tipo_curto"] == "Relator"])
    pico = int(rel.idxmax()) if rel.max() > 0 else None
    ufs = r[r["regiao"].isin(REGIOES_UF)] if "regiao" in r else r
    fora_uf = tot_ref - ufs["empenhado_bi"].sum()

    per_hab, ano_pop = por_habitante(ufs.groupby("uf")["empenhado_bi"].sum(), pop, ref)
    return {
        "anos": anos,
        "ano_corrente_parcial": ano_corrente in anos,
        "tipos": tipos,
        "total_bi": [_num(v) for v in total],
        "executado_pct": [_num(v) if pd.notna(v) else None for v in executado],
        "autor_identificado_pct": [_num(v) if pd.notna(v) else None for v in autor_ok],
        "ref_por_funcao": _top(r.groupby("funcao")["empenhado_bi"].sum(), 8),
        "ref_por_uf": _top(ufs.groupby("uf")["empenhado_bi"].sum(), 10),
        "ref_por_habitante": per_hab,
        "ano_populacao": ano_pop,
        "ref_por_autor": _top(r[r["autor_ok"]].groupby("autor")["empenhado_bi"].sum(), 10),
        "ref_por_regiao": _top(r[r["regiao"].isin(REGIOES_UF)].groupby("regiao")["empenhado_bi"].sum(), 5) if "regiao" in r else [],
        "destaques": {
            "ano_referencia": int(ref),
            "total_bi": _num(tot_ref),
            "individual_pct": pct(r[r["tipo_curto"].str.startswith("Individual")]["empenhado_bi"].sum()),
            "especial_pct": pct(r[r["tipo_curto"] == "Individual (transferência especial)"]["empenhado_bi"].sum()),
            "relator_pico_ano": pico,
            "relator_pico_bi": _num(rel.max()) if pico else None,
            "relator_total_bi": _num(rel.sum()),
            "autor_identificado_pct": pct(r[r["autor_ok"]]["empenhado_bi"].sum()),
            "fora_de_uf_pct": pct(fora_uf),
            "executado_pct": _num(executado[ref]) if pd.notna(executado[ref]) else None,
        },
    }


def main() -> None:
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    df = pd.read_parquet(entrada)
    ipca = pd.read_parquet(IPCA) if IPCA.exists() else None
    pop = pd.read_parquet(POPULACAO) if POPULACAO.exists() else None
    dados = agregar(df, ipca, pop=pop)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("window.EMD = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    h = dados["destaques"]
    print(f"{dados['anos'][0]}-{dados['anos'][-1]} -> {SAIDA} | {h['ano_referencia']}: R$ {h['total_bi']} bi empenhados")


if __name__ == "__main__":
    main()
