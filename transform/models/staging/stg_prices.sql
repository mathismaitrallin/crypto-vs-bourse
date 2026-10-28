select
    symbol,
    date,
    open,
    high,
    low,
    close,
    -- Prix ajusté des dividendes et splits : base de tous les calculs de rendement.
    adj_close as price,
    volume,
    source,
    ingested_at
from {{ source('raw', 'prices') }}
where adj_close is not null
