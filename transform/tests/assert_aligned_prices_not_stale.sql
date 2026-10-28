{{ config(severity='warn') }}

-- Un prix repris d'il y a plus de 4 jours n'est plus représentatif du marché.
select *
from {{ ref('fct_aligned_returns') }}
where staleness_days > 4
