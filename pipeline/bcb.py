"""Baixa séries do SGS (Banco Central) e salva em Parquet."""
from datetime import date

import pandas as pd
import requests

from pipeline.rede import get_com_retentativas  # noqa: F401 (reexportado)
from pipeline.config import BCB_URL, DATA_INICIAL, RAW_DIR, SERIES_BCB


def parse_sgs(registros: list[dict]) -> pd.DataFrame:
    """Converte a resposta JSON do SGS em DataFrame (data, valor)."""
    df = pd.DataFrame(registros)
    if df.empty:
        return pd.DataFrame({"data": pd.to_datetime([]), "valor": []})
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df[["data", "valor"]].dropna().sort_values("data").reset_index(drop=True)


def baixar_serie(codigo: int) -> pd.DataFrame:
    # O SGS limita consultas longas; pedimos em janelas de 10 anos.
    inicio = pd.to_datetime(DATA_INICIAL, format="%d/%m/%Y").year
    fim = date.today().year
    partes = []
    for ano in range(inicio, fim + 1, 10):
        params = {
            "formato": "json",
            "dataInicial": f"01/01/{ano}",
            "dataFinal": f"31/12/{min(ano + 9, fim)}",
        }
        r = get_com_retentativas(BCB_URL.format(codigo=codigo), params)
        partes.append(parse_sgs(r.json()))
    return pd.concat(partes, ignore_index=True).drop_duplicates("data")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for nome, codigo in SERIES_BCB.items():
        df = baixar_serie(codigo)
        destino = RAW_DIR / f"bcb_{nome}.parquet"
        df.to_parquet(destino, index=False)
        print(f"{nome}: {len(df)} linhas -> {destino}")


if __name__ == "__main__":
    main()
