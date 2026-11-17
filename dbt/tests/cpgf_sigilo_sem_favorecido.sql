{{ config(tags=['cpgf']) }}
-- Transações sigilosas não divulgam favorecido. Se divulgarem, o sigilo deixou de ser sigilo.
select *
from {{ ref('stg_cpgf') }}
where sigiloso and favorecido_nome is not null
