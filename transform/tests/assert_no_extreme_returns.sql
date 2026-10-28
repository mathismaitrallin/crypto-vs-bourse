{{ config(severity='warn') }}

-- Une variation de plus de 50 % en un jour est presque toujours une erreur de données.
-- Simple alerte : en crypto, ça peut aussi être un vrai krach, à vérifier à la main.
select *
from {{ ref('fct_daily_returns') }}
where abs(simple_return) > 0.5
