-- Cryptomonnaies tendance, enrichies de leur historique dans le classement.
--
-- Les séries consécutives se comptent en jours de collecte, pas en jours calendaires :
-- un jour où le pipeline n'a pas tourné ne doit pas casser la série d'une cryptomonnaie.

with snapshots as (
    select
        snapshot_date,
        row_number() over (order by snapshot_date) as snapshot_number
    from (select distinct snapshot_date from {{ ref('stg_trending') }})
),

numbered as (
    select
        t.*,
        s.snapshot_number,
        -- Méthode « gaps and islands » : ce numéro reste constant tant que la
        -- cryptomonnaie apparaît à chaque collecte, et change dès qu'elle en rate une.
        s.snapshot_number
            - row_number() over (partition by t.coin_id order by t.snapshot_date) as streak_id
    from {{ ref('stg_trending') }} t
    join snapshots s using (snapshot_date)
)

select
    snapshot_date,
    position,
    coin_id,
    symbol,
    name,
    market_cap_rank,
    price_usd,
    change_24h,
    market_cap_usd,
    volume_24h_usd,
    image_url,
    -- Nombre de jours en tendance jusqu'à cette date incluse.
    row_number() over (partition by coin_id order by snapshot_date) as days_trending,
    -- Jours consécutifs en tendance jusqu'à cette date incluse.
    row_number() over (partition by coin_id, streak_id order by snapshot_date) as streak_days,
    min(snapshot_date) over (partition by coin_id) as first_seen
from numbered
