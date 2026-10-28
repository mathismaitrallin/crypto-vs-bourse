{#
    Rendements de tous les actifs sur un calendrier commun (jours de bourse US).
    C'est la table à utiliser pour les corrélations et les portefeuilles.

    - Crypto : le rendement du lundi couvre vendredi → lundi, week-end compris,
      exactement comme pour une action. Aucune information n'est perdue.
    - Actifs cotés ailleurs (CAC 40) : un jour où Paris est fermé mais New York
      ouvert, on reprend le dernier prix connu (is_carried_forward = true).

    Limite connue : les heures de clôture diffèrent (00:00 UTC pour Binance,
    environ 21:00 UTC pour New York, 16:30 UTC pour Paris).
#}
with grid as (
    select a.symbol, c.date
    from {{ ref('stg_assets') }} a
    cross join {{ ref('int_reference_calendar') }} c
),

-- Pour chaque jour du calendrier, le dernier prix connu à cette date.
as_of_prices as (
    select
        g.symbol,
        g.date,
        p.price,
        p.date as quote_date
    from grid g
    asof left join {{ ref('stg_prices') }} p
        on g.symbol = p.symbol
       and g.date >= p.date
),

with_previous as (
    select
        *,
        lag(price) over (partition by symbol order by date) as prev_price
    from as_of_prices
    -- Avant la première cotation de l'actif (ex. Solana avant 2020), pas de ligne.
    where price is not null
)

select
    symbol,
    date,
    price,
    quote_date,
    quote_date < date                    as is_carried_forward,
    date_diff('day', quote_date, date)   as staleness_days,
    price / prev_price - 1               as simple_return,
    ln(price / prev_price)               as log_return
from with_previous
where prev_price is not null
