{{ config(tags=['despesas']) }}
-- Orçamento da despesa federal (Portal da Transparência), uma linha por ano x classificação.
-- Valores nominais em R$; o "realizado" é a execução do próprio ano (sem restos a pagar).
select
    cast(ano as integer) as ano,
    orgao_superior,
    funcao,
    cast(grupo_cod as varchar) as grupo_cod,
    grupo,
    cast(atualizado as double) as atualizado,
    cast(realizado as double) as realizado
from {{ raw_parquet('orcamento_despesa') }}
where ano is not null and realizado is not null
