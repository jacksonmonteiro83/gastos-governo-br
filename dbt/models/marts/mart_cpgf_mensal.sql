{{ config(tags=['cpgf']) }}
-- Cartão corporativo por mês de extrato e tipo de transação, em R$ de hoje (IPCA do mês do extrato).
-- Meses além do fim da série do IPCA usam fator 1.
select
    s.mes_extrato_data as mes,
    s.ano_extrato as ano,
    s.tipo_transacao,
    count(*) as transacoes,
    sum(s.valor) as valor_nominal,
    sum(s.valor * coalesce(i.fator_para_hoje, 1)) as valor_real
from {{ ref('stg_cpgf') }} s
left join {{ ref('ipca_indice') }} i on i.data = s.mes_extrato_data
group by 1, 2, 3
