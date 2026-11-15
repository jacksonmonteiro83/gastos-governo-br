"""Agrega a série mensal normalizada do Tesouro em totais anuais para o dashboard.

Entrada : data/raw/tesouro_rtn_mensal.parquet (gerado por pipeline.tesouro)
Saída   : docs/data.js  (window.DADOS = {...}), lido pelo dashboard estático

Usa a tabela 1.2-A (valores constantes, IPCA de `referencia`), então todos os anos
são comparáveis. Valores em R$ bilhões. Juros = juros nominais do governo central
(critério abaixo-da-linha, fonte BCB), com sinal invertido para virar "juros pagos".
"""
import json
import sys
from pathlib import Path

import pandas as pd

ENTRADA = Path("data/raw/tesouro_rtn_mensal.parquet")
SAIDA = Path("docs/data.js")
TABELA = "1.2-A"

# chave -> (rótulo, códigos da tabela 1.2-A que somam, sinal)
SERIES = {
    "juros": ("Juros da dívida", ["9"], -1),
    "previdencia": ("Benefícios previdenciários", ["4.1"], 1),
    "pessoal": ("Pessoal e encargos", ["4.2"], 1),
    "outras_obrigatorias": ("Outras despesas obrigatórias", ["4.3"], 1),
    "executivo": ("Despesas do Executivo (programação financeira)", ["4.4"], 1),
    "saude": ("Saúde", ["4.4.1.3", "4.4.2.1"], 1),
    "educacao": ("Educação", ["4.4.1.4", "4.4.2.2"], 1),
    "investimento": ("Investimento", None, 1),  # linha de memorando, sem código
}
DESPESA_PRIMARIA = "4"
# Séries que só existem a partir de certo ano: a fonte traz zeros antes disso,
# que não significam "gasto zero" e viram nulos (None) na saída.
SERIES_COM_INICIO_TARDIO = ["saude", "educacao", "investimento"]


def anular_zeros_iniciais(serie: pd.Series) -> pd.Series:
    """Troca por NaN os anos anteriores ao primeiro valor diferente de zero."""
    nao_zero = serie.ne(0) & serie.notna()
    if not nao_zero.any():
        return serie
    primeiro = nao_zero.idxmax()
    return serie.where(serie.index >= primeiro)


def _num(v):
    return None if pd.isna(v) else round(float(v), 2)


def _mensal(a: pd.DataFrame, chave: str) -> pd.Series:
    rotulo, codigos, sinal = SERIES[chave]
    if chave == "investimento":
        sel = a[a["codigo"].isna() & (a["descricao"] == "Investimento")]
    else:
        sel = a[a["codigo"].isin(codigos)]
        if chave == "juros":
            sel = sel[sel["descricao"].str.startswith("JUROS NOMINAIS")]
    if sel.empty:
        raise ValueError(f"Série '{chave}' não encontrada na tabela {TABELA}.")
    return sinal * sel.groupby("data")["valor"].sum()


def agregar(df: pd.DataFrame) -> dict:
    a = df[df["tabela"] == TABELA].copy()
    a["data"] = pd.to_datetime(a["data"])
    mensais = {k: _mensal(a, k) for k in SERIES}
    despesa = a[(a["codigo"] == DESPESA_PRIMARIA) & (a["nivel"] == 1)].set_index("data")["valor"]

    # só meses presentes em todas as séries (juros costuma sair um mês depois)
    ultimo = min(s.index.max() for s in [*mensais.values(), despesa])
    mensais = {k: s[s.index <= ultimo] for k, s in mensais.items()}
    despesa = despesa[despesa.index <= ultimo]

    anual = pd.DataFrame({k: s.groupby(s.index.year).sum() / 1e3 for k, s in mensais.items()})
    for k in SERIES_COM_INICIO_TARDIO:
        anual[k] = anular_zeros_iniciais(anual[k])
    anual["despesa_primaria"] = despesa.groupby(despesa.index.year).sum() / 1e3
    meses = despesa.groupby(despesa.index.year).size()
    anos = [int(y) for y in anual.index]

    completos = [int(y) for y in meses.index if meses[y] == 12]
    ano_ref = completos[-1]
    juros_total = mensais["juros"].sum() / 1e6  # R$ tri
    gasto_total = juros_total + despesa.sum() / 1e6

    referencia = a["referencia"].dropna().iloc[0]
    return {
        "referencia": referencia,
        "ultimo_mes": ultimo.strftime("%Y-%m"),
        "anos": anos,
        "meses": [int(meses[y]) for y in anual.index],
        "series": {
            k: {"rotulo": SERIES[k][0], "valores": [_num(v) for v in anual[k]]}
            for k in SERIES
        },
        "despesa_primaria": [_num(v) for v in anual["despesa_primaria"]],
        "destaques": {
            "juros_total_tri": round(float(juros_total), 2),
            "juros_pct_gasto_total": round(float(100 * juros_total / gasto_total), 1),
            "ano_referencia": ano_ref,
            "juros_ano_bi": round(float(anual.loc[ano_ref, "juros"]), 1),
            "juros_por_dia_bi": round(float(anual.loc[ano_ref, "juros"] / 365), 2),
            "saude_ano_bi": round(float(anual.loc[ano_ref, "saude"]), 1),
            "educacao_ano_bi": round(float(anual.loc[ano_ref, "educacao"]), 1),
            "investimento_ano_bi": round(float(anual.loc[ano_ref, "investimento"]), 1),
        },
    }


def main() -> None:
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    df = pd.read_csv(entrada) if entrada.suffix == ".csv" else pd.read_parquet(entrada)
    dados = agregar(df)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        "window.DADOS = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )
    print(f"{len(dados['anos'])} anos -> {SAIDA}")


if __name__ == "__main__":
    main()
