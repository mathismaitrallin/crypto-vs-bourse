{#
    Rendements journaliers de chaque actif sur SON propre calendrier :
    7 jours sur 7 pour la crypto, jours de bourse pour les autres.
    À utiliser pour étudier un actif isolément (volatilité, drawdowns...).
    Pour comparer des actifs entre eux, utiliser fct_aligned_returns.
#}
with prices as (
    select
        symbol,
        date,
        price,
        lag(price) over (partition by symbol order by date) as prev_price,
        lag(date)  over (partition by symbol order by date) as prev_date
    from {{ ref('stg_prices') }}
)

select
    symbol,
    date,
    price,
    price / prev_price - 1          as simple_return,
    ln(price / prev_price)          as log_return,
    date_diff('day', prev_date, date) as days_since_prev
from prices
where prev_price is not null
