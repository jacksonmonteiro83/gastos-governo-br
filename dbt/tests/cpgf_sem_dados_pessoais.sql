{{ config(tags=['cpgf']) }}
-- Privacidade: nome e CNPJ só podem existir para empresas (pj). Qualquer linha aqui é falha.
select *
from {{ ref('stg_cpgf') }}
where favorecido_tipo <> 'pj'
  and (favorecido_nome is not null or favorecido_cnpj is not null)
