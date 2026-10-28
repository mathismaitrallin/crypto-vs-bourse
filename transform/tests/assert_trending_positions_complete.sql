-- Chaque photo du classement doit être complète : positions 1, 2, …, N sans trou.
select
    snapshot_date,
    count(*) as nb_cryptomonnaies,
    min(position) as premiere_position,
    max(position) as derniere_position
from {{ ref('stg_trending') }}
group by snapshot_date
having min(position) <> 1 or max(position) <> count(*)
