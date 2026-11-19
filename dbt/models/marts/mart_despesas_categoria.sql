{{ config(tags=['despesas']) }}
-- Composição da despesa por ano, sem sobreposição (cada linha entra na primeira categoria que a descreve):
-- previdência (função) > juros > pessoal > saúde/educação/assistência > investimentos > outras.
-- Mesma regra de pipeline/agregar_despesas.py. R$ bi de hoje (fator médio do IPCA no ano; 1 sem IPCA).
-- Ficam fora a amortização/refinanciamento da dívida (grupo 6) e a reserva de contingência (grupo 9).
with fator as (
    select year(data) as ano, avg(fator_para_hoje) as fator
    from {{ ref('ipca_indice') }}
    group by 1
),
base as (
    select
        d.ano,
        d.realizado * coalesce(f.fator, 1) / 1e9 as real_bi,
        case
            when lower(d.funcao) like '%previd%' then 'Previdência social'
            when d.grupo = 'Juros e Encargos da Dívida' then 'Juros da dívida'
            when d.grupo = 'Pessoal e Encargos Sociais' then 'Pessoal e encargos'
            when lower(d.funcao) like '%saúde%' or lower(d.funcao) like '%educa%' or lower(d.funcao) like '%assist%'
                then 'Saúde, educação e assistência'
            when d.grupo = 'Investimentos' then 'Investimentos'
            else 'Outras'
        end as categoria
    from {{ ref('stg_despesas') }} d
    left join fator f using (ano)
    where coalesce(d.grupo_cod, '') not in ('6', '9')
),
agg as (
    select ano, categoria, sum(real_bi) as bi from base group by 1, 2
)
select
    ano,
    categoria,
    round(bi, 1) as bi,
    round(100 * bi / sum(bi) over (partition by ano), 1) as pct
from agg
order by ano, categoria
