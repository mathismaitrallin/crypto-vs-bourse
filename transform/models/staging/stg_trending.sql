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
    fetched_at
from {{ source('raw', 'trending') }}
