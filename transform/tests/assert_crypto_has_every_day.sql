-- La crypto cote 7j/7 : un jour manquant signale un trou dans la collecte.
select r.*
from {{ ref('fct_daily_returns') }} r
join {{ ref('stg_assets') }} a using (symbol)
where a.asset_class = 'crypto'
  and r.days_since_prev > 1
