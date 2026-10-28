{#
    Par défaut, dbt préfixe les schémas personnalisés (main_staging, main_marts).
    On utilise directement le nom donné : staging, intermediate, marts.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
