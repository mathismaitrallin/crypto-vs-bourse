-- Un prix doit être positif et la clôture comprise entre le plus bas et le plus haut du jour.
select *
from {{ ref('stg_prices') }}
where price <= 0
   or high < low
   or close > high
   or close < low
