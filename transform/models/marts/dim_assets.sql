with history as (
    select
        symbol,
        min(date) as first_date,
        max(date) as last_date,
        count(*)  as nb_quotes
    from {{ ref('stg_prices') }}
    group by symbol
)

select
    a.symbol,
    a.name,
    a.asset_class,
    a.source,
    -- Nombre de périodes par an pour annualiser rendements et volatilités :
    -- la crypto cote tous les jours, les autres actifs environ 252 jours par an.
    case when a.asset_class = 'crypto' then 365 else 252 end as periods_per_year,
    h.first_date,
    h.last_date,
    h.nb_quotes
from {{ ref('stg_assets') }} a
left join history h using (symbol)
