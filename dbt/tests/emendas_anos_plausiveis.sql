{{ config(tags=['emendas']) }}
-- O arquivo do Portal começa em 2014; ano fora de 2014..ano atual indica coluna lida errada.
select ano from {{ ref('mart_emendas_anual') }}
where ano < 2014 or ano > year(current_date)
