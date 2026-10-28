select
    symbol,
    name,
    asset_class,
    source,
    source_ticker
from {{ source('raw', 'assets') }}
