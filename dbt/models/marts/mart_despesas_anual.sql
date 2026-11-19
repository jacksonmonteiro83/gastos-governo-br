{{ config(tags=['despesas']) }}
-- Totais anuais da despesa federal realizada, R$ bi de hoje. "Total" exclui amortização (6) e reserva (9).
with fator as (
    select year(data) as ano, avg(fator_para_hoje) as fator
    from {{ ref('ipca_indice') }}
    group by 1
),
base as (
    select
        d.ano,
        d.realizado * coalesce(f.fator, 1) / 1e9 as real_bi,
        d.atualizado * coalesce(f.fator, 1) / 1e9 as atual_bi,
        coalesce(d.grupo_cod, '') as grupo_cod
    from {{ ref('stg_despesas') }} d
    left join fator f using (ano)
)
select
    ano,
    ano < year(current_date) as ano_completo,
    round(sum(real_bi) filter (where grupo_cod not in ('6', '9')), 1) as total_bi,
    round(sum(real_bi) filter (where grupo_cod = '6'), 1) as amortizacao_bi,
    round(100 * sum(real_bi) filter (where grupo_cod not in ('6', '9'))
              / nullif(sum(atual_bi) filter (where grupo_cod not in ('6', '9')), 0), 1) as execucao_pct
from base
group by 1
order by 1
