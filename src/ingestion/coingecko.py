"""Cryptomonnaies tendance du jour, depuis l'API publique de CoinGecko.

« Tendance » = les cryptomonnaies les plus recherchées sur CoinGecko au cours
des dernières 24 heures, de la plus populaire à la moins populaire. Aucune clé
d'API n'est nécessaire. L'API ne donne que le classement du moment : l'historique
se construit en enregistrant une photo par jour.
"""
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

COLUMNS = [
    "snapshot_date", "position", "coin_id", "symbol", "name", "market_cap_rank",
    "price_usd", "change_24h", "market_cap_usd", "volume_24h_usd", "image_url",
]


def _dollars(text: Optional[str]) -> Optional[float]:
    """« $2,083,667,152 » → 2083667152.0 ; vide ou illisible → None."""
    if not text:
        return None
    try:
        return float(str(text).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def fetch_trending() -> pd.DataFrame:
    resp = requests.get(TRENDING_URL, headers={"accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    coins = resp.json().get("coins", [])

    snapshot_date = datetime.now(timezone.utc).date()
    rows = []
    for position, entry in enumerate(coins, start=1):
        item = entry["item"]
        quote = item.get("data") or {}
        change = (quote.get("price_change_percentage_24h") or {}).get("usd")
        rows.append(
            {
                "snapshot_date": snapshot_date,
                "position": position,
                "coin_id": item["id"],
                "symbol": item["symbol"].upper(),
                "name": item["name"],
                "market_cap_rank": item.get("market_cap_rank"),
                "price_usd": quote.get("price"),
                "change_24h": None if change is None else change / 100,
                "market_cap_usd": _dollars(quote.get("market_cap")),
                "volume_24h_usd": _dollars(quote.get("total_volume")),
                "image_url": item.get("small") or item.get("thumb"),
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)
