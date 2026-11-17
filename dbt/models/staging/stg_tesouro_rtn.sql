-- Resultado do Tesouro Nacional, formato longo (uma linha por tabela x mês x linha da planilha).
-- Valores em R$ milhões. Tabelas "-A" estão em valores constantes (IPCA).
select
    tabela,
    cast(data as date) as data,
    codigo,
    nivel,
    descricao,
    valor
from {{ raw_parquet('tesouro_rtn_mensal') }}
where valor is not null
