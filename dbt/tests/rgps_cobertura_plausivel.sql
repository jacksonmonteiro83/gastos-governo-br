-- Cobertura (arrecadação / benefícios) fora de 30%-120% em ano completo indica linha errada na planilha.
select * from {{ ref('mart_rgps_anual') }}
where ano_completo and cobertura_pct not between 30 and 120
