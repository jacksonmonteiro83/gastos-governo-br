from pathlib import Path

RAW_DIR = Path("data/raw")

# Séries do Banco Central (SGS): nome -> código
SERIES_BCB = {
    "ipca_mensal": 433,    # IPCA, variação mensal (%)
    "selic_mensal": 4390,  # Selic acumulada no mês (%)
    "pib_12m": 4382,       # PIB acumulado nos últimos 12 meses (R$ milhões)
}

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
DATA_INICIAL = "01/01/1997"  # início da série do Resultado do Tesouro
