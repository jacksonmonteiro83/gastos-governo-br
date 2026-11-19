{{ config(tags=['emendas']) }}
-- Total empenhado por ano (R$ bi de hoje) e taxa de execução: (pago no ano + restos a pagar pagos) / empenhado.
with fator as (
    select year(data) as ano, avg(fator_para_hoje) as fator
    from {{ ref('ipca_indice') }}
    group by 1
)
select
    e.ano,
    round(sum(e.empenhado * coalesce(f.fator, 1)) / 1e9, 1) as total_bi,
    round(100 * sum(e.pago + e.rap_pago) / nullif(sum(e.empenhado), 0), 1) as executado_pct
from {{ ref('stg_emendas') }} e
left join fator f using (ano)
group by 1
order by 1
