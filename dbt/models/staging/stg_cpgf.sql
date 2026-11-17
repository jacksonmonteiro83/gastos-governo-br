{{ config(tags=['cpgf']) }}
-- Cartão de pagamento do governo federal (CPGF), já sem portadores e sem pessoa física/MEI.
select
    cast(ano_extrato as integer) as ano_extrato,
    cast(mes_extrato as integer) as mes_extrato,
    make_date(cast(ano_extrato as integer), cast(mes_extrato as integer), 1) as mes_extrato_data,
    orgao_superior,
    orgao,
    cast(data_transacao as date) as data_transacao,
    tipo_transacao,
    sigiloso,
    favorecido_tipo,
    favorecido_cnpj,
    favorecido_nome,
    valor
from {{ raw_parquet('cpgf_normalizado') }}
where ano_extrato is not null and mes_extrato is not null and valor is not null
