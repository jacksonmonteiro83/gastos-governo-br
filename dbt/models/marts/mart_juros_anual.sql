-- Juros nominais do governo central por ano (linha 9, abaixo-da-linha, sinal invertido = juros pagos),
-- R$ bilhões constantes, e peso sobre (juros + despesa primária).
with juros as (
    select data, -sum(valor) as valor
    from {{ ref('stg_tesouro_rtn') }}
    where tabela = '1.2-A' and codigo = '9'
    group by data
),
despesa as (
    select data, sum(valor) as valor
    from {{ ref('stg_tesouro_rtn') }}
    where tabela = '1.2-A' and codigo = '4' and nivel = 1
    group by data
)
select
    year(j.data) as ano,
    count(*) as meses,
    count(*) = 12 as ano_completo,
    round(sum(j.valor) / 1000, 2) as juros_bi,
    round(sum(d.valor) / 1000, 2) as despesa_primaria_bi,
    round(100 * sum(j.valor) / (sum(j.valor) + sum(d.valor)), 1) as juros_pct_gasto_total
from juros j
join despesa d using (data)
group by 1
order by 1
