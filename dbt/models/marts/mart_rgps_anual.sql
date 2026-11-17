-- Previdência do INSS (RGPS) por ano, R$ bilhões constantes (IPCA).
-- Arrecadação líquida (linha 1.3) x benefícios previdenciários (linha 4.1) da tabela 1.2-A do RTN.
-- Necessidade de financiamento = benefícios - arrecadação. Só entram meses com as duas linhas.
with base as (
    select data, codigo, upper(descricao) as descricao, valor
    from {{ ref('stg_tesouro_rtn') }}
    where tabela = '1.2-A'
),
arrecadacao as (
    select data, sum(valor) as valor
    from base where codigo = '1.3' and descricao like '%RGPS%'
    group by data
),
beneficios as (
    select data, sum(valor) as valor
    from base where codigo = '4.1' and descricao like '%BENEF%'
    group by data
),
despesa as (
    select data, sum(valor) as valor
    from {{ ref('stg_tesouro_rtn') }}
    where tabela = '1.2-A' and codigo = '4' and nivel = 1
    group by data
),
mensal as (
    select a.data,
           a.valor as arrecadacao,
           b.valor as beneficios,
           d.valor as despesa_primaria
    from arrecadacao a
    join beneficios b using (data)
    join despesa d using (data)
)
select
    year(data) as ano,
    count(*) as meses,
    count(*) = 12 as ano_completo,
    round(sum(arrecadacao) / 1000, 2) as arrecadacao_bi,
    round(sum(beneficios) / 1000, 2) as beneficios_bi,
    round(sum(beneficios - arrecadacao) / 1000, 2) as necessidade_bi,
    round(100 * sum(arrecadacao) / sum(beneficios), 1) as cobertura_pct,
    round(100 * sum(beneficios) / sum(despesa_primaria), 1) as beneficios_pct_despesa_primaria
from mensal
group by 1
order by 1
