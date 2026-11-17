{{ config(tags=['cpgf']) }}
select
    ano,
    count(distinct mes) as meses,
    count(distinct mes) = 12 as ano_completo,
    round(sum(valor_real) / 1e6, 2) as total_real_mi,
    round(100 * sum(valor_real) filter (where tipo_transacao = 'sigilo') / sum(valor_real), 1) as sigilo_pct,
    round(100 * sum(valor_real) filter (where tipo_transacao = 'saque') / sum(valor_real), 1) as saque_pct,
    sum(transacoes) as transacoes
from {{ ref('mart_cpgf_mensal') }}
group by 1
order by 1
