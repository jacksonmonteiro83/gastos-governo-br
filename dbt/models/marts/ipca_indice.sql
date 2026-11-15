-- Índice acumulado do IPCA (base 100 no primeiro mês) e fator para
-- trazer qualquer valor histórico para o último mês disponível.
with acumulado as (
    select
        data,
        100 * exp(sum(ln(1 + variacao_pct / 100)) over (order by data)) as indice
    from {{ ref('stg_ipca') }}
)
select
    data,
    indice,
    (select max_by(indice, data) from acumulado) / indice as fator_para_hoje
from acumulado
