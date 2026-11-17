{{ config(tags=['cpgf']) }}
-- Uma linha por mês x tipo de transação.
select mes, tipo_transacao, count(*) as n
from {{ ref('mart_cpgf_mensal') }}
group by 1, 2
having count(*) > 1
