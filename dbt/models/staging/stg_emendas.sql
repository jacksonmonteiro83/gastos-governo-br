{{ config(tags=['emendas']) }}
-- Emendas parlamentares (Portal da Transparência), uma linha por emenda x localidade x ação. R$ nominais.
select
    cast(ano as integer) as ano,
    tipo,
    autor,
    uf,
    regiao,
    funcao,
    cast(empenhado as double) as empenhado,
    coalesce(cast(pago as double), 0) as pago,
    coalesce(cast(rap_pago as double), 0) as rap_pago
from {{ raw_parquet('emendas') }}
where ano is not null and empenhado is not null
