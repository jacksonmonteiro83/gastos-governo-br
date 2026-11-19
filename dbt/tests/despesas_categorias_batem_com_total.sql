{{ config(tags=['despesas']) }}
-- A soma das categorias em R$ deve bater com o total anual (tolerância de arredondamento).
select c.ano, sum(c.bi) as soma_categorias, max(a.total_bi) as total
from {{ ref('mart_despesas_categoria') }} c
join {{ ref('mart_despesas_anual') }} a using (ano)
group by 1
having abs(sum(c.bi) - max(a.total_bi)) > 0.5
