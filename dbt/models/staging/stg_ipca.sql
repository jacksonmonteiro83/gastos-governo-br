select
    cast(data as date) as data,
    valor as variacao_pct
from {{ raw_parquet('bcb_ipca_mensal') }}
