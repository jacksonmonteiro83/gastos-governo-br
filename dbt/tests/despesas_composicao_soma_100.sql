{{ config(tags=['despesas']) }}
-- As categorias de cada ano devem somar 100% (tolerância de arredondamento de uma casa em 6 categorias).
select ano, round(sum(pct), 1) as soma
from {{ ref('mart_despesas_categoria') }}
group by 1
having abs(sum(pct) - 100) > 0.4
