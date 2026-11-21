"""População residente estimada por UF (IBGE, SIDRA tabela 6579), para calcular valores por habitante.

Saída: data/raw/populacao_uf.parquet com uf_cod, uf (nome), ano, populacao.
A tabela não tem todos os anos (ficam de fora os anos de Censo, como 2022 e 2023); quem usa
escolhe o ano mais recente disponível até o ano pedido.

    python -m pipeline.populacao_uf
"""
import pandas as pd

from pipeline.config import RAW_DIR
from pipeline.rede import get_com_retentativas

URL = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/all"
SAIDA = RAW_DIR / "populacao_uf.parquet"


def normalizar(linhas: list[dict]) -> pd.DataFrame:
    """Resposta do SIDRA (lista de dicts; a primeira linha é o cabeçalho) -> DataFrame limpo."""
    df = pd.DataFrame(linhas[1:])
    out = pd.DataFrame({
        "uf_cod": df["D1C"].astype(int),
        "uf": df["D1N"].astype(str),
        "ano": df["D3C"].astype(int),
        "populacao": pd.to_numeric(df["V"], errors="coerce"),
    })
    return out.dropna(subset=["populacao"]).sort_values(["ano", "uf_cod"]).reset_index(drop=True)


def main() -> None:
    r = get_com_retentativas(URL, timeout=120)
    print(f"GET {URL} -> HTTP {r.status_code}")
    r.raise_for_status()
    df = normalizar(r.json())
    if df["uf"].nunique() != 27:
        raise SystemExit(f"Esperava 27 UFs, vieram {df['uf'].nunique()}")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA, index=False)
    print(f"{len(df)} linhas, anos {df['ano'].min()}-{df['ano'].max()} -> {SAIDA}")


if __name__ == "__main__":
    main()
