-- Em ano completo o governo central pagou juros líquidos (sinal invertido > 0).
select * from {{ ref('mart_juros_anual') }}
where ano_completo and juros_bi <= 0
