{{ config(tags=['emendas']) }}
-- Empenhado por ano e tipo de emenda, R$ bi de hoje (fator médio do IPCA no ano da emenda; 1 sem IPCA).
-- Rótulos curtos iguais aos de pipeline/agregar_emendas.py.
with fator as (
    select year(data) as ano, avg(fator_para_hoje) as fator
    from {{ ref('ipca_indice') }}
    group by 1
)
select
    e.ano,
    case e.tipo
        when 'Emenda Individual - Transferências com Finalidade Definida' then 'Individual (finalidade definida)'
        when 'Emenda Individual - Transferências Especiais' then 'Individual (transferência especial)'
        when 'Emenda de Bancada' then 'Bancada'
        when 'Emenda de Comissão' then 'Comissão'
        when 'Emenda de Relator' then 'Relator'
        else e.tipo
    end as tipo,
    round(sum(e.empenhado * coalesce(f.fator, 1)) / 1e9, 1) as bi
from {{ ref('stg_emendas') }} e
left join fator f using (ano)
group by 1, 2
order by 1, 2
