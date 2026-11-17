{# Lê um Parquet gerado pelo pipeline Python em data/raw/. O dbt roda de dentro de dbt/. #}
{% macro raw_parquet(nome) -%}
    read_parquet('../data/raw/{{ nome }}.parquet')
{%- endmacro %}
