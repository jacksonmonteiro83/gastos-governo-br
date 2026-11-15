select
    cast(data as date) as data,
    valor as variacao_pct
from read_parquet('../data/raw/bcb_ipca_mensal.parquet')
