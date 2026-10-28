"""Collecte des prix de tous les actifs et des cryptomonnaies tendance, écriture dans DuckDB.

Usage :
    python -m src.ingest                 # mise à jour incrémentale
    python -m src.ingest --full-refresh  # re-télécharge tout l'historique
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

from src.config import ASSETS, LOOKBACK_DAYS, START_DATE, TRENDING_HISTORY_PATH
from src.db import (
    connect,
    delete_prices,
    get_last_date,
    init_schema,
    replace_trending_snapshot,
    restore_trending,
    upsert_assets,
    upsert_prices,
)
from src.ingestion import binance, coingecko, yahoo

FETCHERS = {
    "binance": binance.fetch_daily,
    "yahoo": yahoo.fetch_daily,
}


def run(full_refresh: bool = False) -> int:
    con = connect()
    init_schema(con)
    upsert_assets(con, ASSETS)

    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    failures = []

    for asset in ASSETS:
        last = None if full_refresh else get_last_date(con, asset.symbol)
        start = START_DATE if last is None else (last - timedelta(days=LOOKBACK_DAYS)).isoformat()

        try:
            df = FETCHERS[asset.source](asset.source_ticker, start)
        except Exception as exc:  # une source en panne ne doit pas bloquer les autres
            print(f"  ✗ {asset.symbol:<5} échec : {exc}")
            failures.append(asset.symbol)
            continue

        if df.empty:
            print(f"  · {asset.symbol:<5} rien de nouveau depuis {start}")
            continue

        if full_refresh:
            delete_prices(con, asset.symbol)

        df["symbol"] = asset.symbol
        df["source"] = asset.source
        df["ingested_at"] = ingested_at
        n = upsert_prices(con, df)
        print(f"  ✓ {asset.symbol:<5} {n:>5} lignes ({df['date'].min()} → {df['date'].max()})")

    collect_trending(con, ingested_at)
    con.close()

    if failures:
        print(f"\n{len(failures)} actif(s) en échec : {', '.join(failures)}")
        return 1
    print("\nCollecte terminée.")
    return 0


def collect_trending(con, fetched_at) -> None:
    """Ajoute la photo du jour des tendances CoinGecko à l'historique.

    Non bloquant : une panne de CoinGecko ne doit pas empêcher la mise à jour des prix.
    Le test de fraîcheur dbt (source raw.trending) signale si les photos s'arrêtent.
    """
    if TRENDING_HISTORY_PATH.exists():
        n = restore_trending(con, str(TRENDING_HISTORY_PATH))
        print(f"\n  ↺ tendances : {n} lignes d'historique restaurées")
    try:
        df = coingecko.fetch_trending()
    except Exception as exc:
        print(f"  ⚠ tendances : échec CoinGecko ({exc}), historique inchangé")
        return
    if df.empty:
        print("  ⚠ tendances : classement vide, historique inchangé")
        return
    df["fetched_at"] = fetched_at
    n = replace_trending_snapshot(con, df)
    print(f"  ✓ tendances : {n} cryptomonnaies au {df['snapshot_date'].iloc[0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full-refresh", action="store_true", help="re-télécharge tout l'historique")
    args = parser.parse_args()
    sys.exit(run(full_refresh=args.full_refresh))
