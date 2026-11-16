"""Valida os juros nominais do Tesouro (RTN, tabela 1.2) contra séries do Banco Central (SGS).

Compara, mês a mês e por ano, em valores correntes (R$ milhões):
  - SGS 4606: NFSP sem desvalorização cambial, fluxo mensal, juros nominais, Governo Federal e Banco Central
  - SGS 4607: idem, só Governo Federal

Uso (precisa de rede para o portal do Tesouro e para api.bcb.gov.br; rode no GitHub Actions):
    python -m pipeline.validar_juros
"""
import pandas as pd

from pipeline.bcb import baixar_serie
from pipeline.config import RAW_DIR

SERIES_BCB = {4606: "Governo Federal e Banco Central", 4607: "Governo Federal"}
TESOURO = RAW_DIR / "tesouro_rtn_mensal.parquet"


def juros_tesouro(df: pd.DataFrame) -> pd.Series:
    """Juros pagos por mês (positivo = despesa), R$ milhões correntes, índice Period M."""
    a = df[(df["tabela"] == "1.2") & df["descricao"].str.startswith("JUROS NOMINAIS", na=False)]
    s = -a.assign(data=pd.to_datetime(a["data"])).groupby("data")["valor"].sum()
    s.index = s.index.to_period("M")
    return s


def serie_bcb(df: pd.DataFrame) -> pd.Series:
    s = df.assign(data=pd.to_datetime(df["data"])).set_index("data")["valor"]
    s.index = s.index.to_period("M")
    return s


def comparar(tesouro: pd.Series, bcb: pd.Series) -> tuple[pd.DataFrame, dict]:
    """Devolve (tabela anual, resumo mensal). Usa só os meses presentes nas duas séries."""
    j = pd.concat({"tesouro": tesouro, "bcb": bcb}, axis=1).dropna()
    corr = float(j["tesouro"].corr(j["bcb"]))
    sinal_invertido = corr < 0
    if sinal_invertido:
        j["bcb"] = -j["bcb"]
        corr = -corr
    dif_pct_mes = (j["tesouro"] - j["bcb"]).abs() / j["bcb"].abs().where(j["bcb"].abs() > 1)
    anual = j.groupby(j.index.year).sum()
    anual["dif"] = anual["tesouro"] - anual["bcb"]
    anual["dif_pct"] = 100 * anual["dif"] / anual["bcb"]
    resumo = {
        "meses": int(len(j)), "correlacao": round(corr, 4), "sinal_invertido": sinal_invertido,
        "dif_media_abs_mensal_pct": round(float(100 * dif_pct_mes.mean()), 2),
        "meses_com_dif_acima_de_5pct": int((dif_pct_mes > 0.05).sum()),
        "total_tesouro_bi": round(float(j["tesouro"].sum() / 1e3), 1),
        "total_bcb_bi": round(float(j["bcb"].sum() / 1e3), 1),
    }
    return anual.round(1), resumo


def main() -> None:
    tesouro = juros_tesouro(pd.read_parquet(TESOURO))
    for codigo, nome in SERIES_BCB.items():
        print(f"\n=== SGS {codigo}: juros nominais, {nome} ===")
        try:
            bcb = serie_bcb(baixar_serie(codigo))
        except Exception as e:  # série pode estar indisponível; não derruba a outra
            print(f"Falha ao baixar a série {codigo}: {e}")
            continue
        anual, resumo = comparar(tesouro, bcb)
        print(resumo)
        print(anual.to_string())


if __name__ == "__main__":
    main()
