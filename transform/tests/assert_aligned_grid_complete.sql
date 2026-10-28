-- Chaque jour du calendrier commun doit avoir une ligne pour chaque actif déjà coté à cette date.
with expected as (
    select a.symbol, c.date
    from {{ ref('dim_assets') }} a
    join {{ ref('int_reference_calendar') }} c
      on c.date > a.first_date
)

select e.*
from expected e
left join {{ ref('fct_aligned_returns') }} r using (symbol, date)
where r.symbol is null
  -- Premier jour du calendrier : pas de jour précédent, donc pas de rendement.
  and e.date > (select min(date) from {{ ref('int_reference_calendar') }})
