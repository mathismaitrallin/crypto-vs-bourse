{#
    Calendrier commun à tous les actifs : les jours de cotation de la bourse US.

    Pourquoi pas tous les jours calendaires ? Remplir les week-ends en recopiant
    le prix du vendredi donnerait aux actions des rendements nuls le samedi et
    le dimanche. Leur volatilité et leur corrélation avec la crypto seraient
    alors artificiellement écrasées.

    On s'arrête au dernier jour pour lequel TOUS les actifs ont une donnée, pour
    ne jamais comparer un prix du jour avec un prix recopié de la veille.
#}
with last_quotes as (
    select symbol, max(date) as last_date
    from {{ ref('stg_prices') }}
    group by symbol
)

select distinct date
from {{ ref('stg_prices') }}
where symbol = '{{ var("reference_calendar_symbol") }}'
  and date <= (select min(last_date) from last_quotes)
