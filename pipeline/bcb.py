"""Baixa séries do SGS (Banco Central) e salva em Parquet."""
import time
from datetime import date

import pandas as pd
import requests

from pipeline.config import BCB_URL, DATA_INICIAL, RAW_DIR, SERIES_BCB


def parse_sgs(registros: list[dict]) -> pd.DataFrame:
    """Converte a resposta JSON do SGS em DataFrame (data, valor)."""
    df = pd.DataFrame(registros)
    if df.empty:
        return pd.DataFrame({"data": pd.to_datetime([]), "valor": []})
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df[["data", "valor"]].dropna().sort_values("data").reset_index(drop=True)


TENTATIVAS = 5
PAUSA_BASE = 5.0  # segundos; dobra a cada falha (5, 10, 20, 40)
_TRANSITORIOS = {429, 500, 502, 503, 504}


def get_com_retentativas(url: str, params: dict, tentativas: int = TENTATIVAS, pausa_base: float = PAUSA_BASE,
                         get=requests.get, dormir=time.sleep) -> requests.Response:
    """GET que tenta de novo em erro transitório do servidor (5xx, 429) ou de rede. 4xx de verdade não repete."""
    for n in range(1, tentativas + 1):
        try:
            r = get(url, params=params, timeout=60)
            if r.status_code not in _TRANSITORIOS:
                r.raise_for_status()
                return r
            erro = f"HTTP {r.status_code}"
        except (requests.ConnectionError, requests.Timeout) as e:
            erro = type(e).__name__
        if n == tentativas:
            raise RuntimeError(f"SGS falhou {tentativas} vezes seguidas ({erro}): {url} {params}")
        espera = pausa_base * 2 ** (n - 1)
        print(f"  SGS {erro}; tentativa {n}/{tentativas}, nova em {espera:.0f}s")
        dormir(espera)


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
