{{ config(severity='warn') }}

-- Le plus long arrêt normal est de 5 jours : à Paris, Vendredi saint + week-end +
-- lundi de Pâques, ou 25-26 décembre + week-end. Au-delà, il manque des données.
select r.*
from {{ ref('fct_daily_returns') }} r
join {{ ref('stg_assets') }} a using (symbol)
where a.asset_class <> 'crypto'
  and r.days_since_prev > 5
