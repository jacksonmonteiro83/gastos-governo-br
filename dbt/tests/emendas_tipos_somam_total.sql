{{ config(tags=['emendas']) }}
-- A soma dos tipos de cada ano deve bater com o total anual (tolerância de arredondamento).
select t.ano, sum(t.bi) as soma_tipos, max(a.total_bi) as total
from {{ ref('mart_emendas_tipo_ano') }} t
join {{ ref('mart_emendas_anual') }} a using (ano)
group by 1
having abs(sum(t.bi) - max(a.total_bi)) > 0.5
