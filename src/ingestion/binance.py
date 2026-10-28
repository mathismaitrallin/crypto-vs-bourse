"""Récupération des bougies journalières depuis l'API publique de Binance.

Aucune clé d'API n'est nécessaire : on utilise l'endpoint public de données
de marché, limité à 1000 bougies par requête (d'où la pagination).
"""
import time

import pandas as pd
import requests

BASE_URL = "https://data-api.binance.vision/api/v3/klines"
PAGE_SIZE = 1000

COLUMNS = ["date", "open", "high", "low", "close", "adj_close", "volume"]


def fetch_daily(ticker: str, start: str) -> pd.DataFrame:
    """Bougies journalières de `ticker` (ex. BTCUSDT) depuis `start` (AAAA-MM-JJ)."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    rows = []

    while True:
        resp = requests.get(
            BASE_URL,
            params={
                "symbol": ticker,
                "interval": "1d",
                "startTime": start_ms,
                "limit": PAGE_SIZE,
            },
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start_ms = batch[-1][0] + 1  # repart juste après la dernière bougie reçue
        time.sleep(0.2)  # on reste poli avec l'API

    # On ne garde que les bougies terminées : celle du jour en cours bouge encore.
    now_ms = int(time.time() * 1000)
    rows = [r for r in rows if r[6] < now_ms]
    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    # Format Binance : [open_time, open, high, low, close, volume, close_time, ...]
    raw = pd.DataFrame([r[:6] for r in rows], columns=["open_time", "open", "high", "low", "close", "volume"])
    prices = raw[["open", "high", "low", "close", "volume"]].astype(float)

    df = pd.DataFrame(
        {
            # Une bougie journalière Binance va de 00:00 à 23:59 UTC.
            "date": pd.to_datetime(raw["open_time"], unit="ms", utc=True).dt.date,
            "open": prices["open"],
            "high": prices["high"],
            "low": prices["low"],
            "close": prices["close"],
            "adj_close": prices["close"],  # pas de dividende ni de split en crypto
            "volume": prices["volume"],
        }
    )
    return df
