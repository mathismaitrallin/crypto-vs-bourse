"""Accès à la base DuckDB : création du schéma et écriture des données brutes."""
from datetime import date
from typing import List, Optional

import duckdb
import pandas as pd

from src.config import DB_PATH, Asset

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.assets (
    symbol        VARCHAR PRIMARY KEY,
    name          VARCHAR NOT NULL,
    asset_class   VARCHAR NOT NULL,
    source        VARCHAR NOT NULL,
    source_ticker VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.prices (
    symbol      VARCHAR   NOT NULL,
    date        DATE      NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    adj_close   DOUBLE,
    volume      DOUBLE,
    source      VARCHAR   NOT NULL,
    ingested_at TIMESTAMP NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS raw.trending (
    snapshot_date   DATE      NOT NULL,
    position        INTEGER   NOT NULL,
    coin_id         VARCHAR   NOT NULL,
    symbol          VARCHAR   NOT NULL,
    name            VARCHAR   NOT NULL,
    market_cap_rank INTEGER,
    price_usd       DOUBLE,
    change_24h      DOUBLE,
    market_cap_usd  DOUBLE,
    volume_24h_usd  DOUBLE,
    image_url       VARCHAR,
    fetched_at      TIMESTAMP NOT NULL,
    PRIMARY KEY (snapshot_date, coin_id)
);
"""

PRICE_COLUMNS = [
    "symbol", "date", "open", "high", "low", "close",
    "adj_close", "volume", "source", "ingested_at",
]

TRENDING_COLUMNS = [
    "snapshot_date", "position", "coin_id", "symbol", "name", "market_cap_rank",
    "price_usd", "change_24h", "market_cap_usd", "volume_24h_usd", "image_url", "fetched_at",
]


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_SQL)


def upsert_assets(con: duckdb.DuckDBPyConnection, assets: List[Asset]) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO raw.assets VALUES (?, ?, ?, ?, ?)",
        [(a.symbol, a.name, a.asset_class, a.source, a.source_ticker) for a in assets],
    )


def get_last_date(con: duckdb.DuckDBPyConnection, symbol: str) -> Optional[date]:
    row = con.execute(
        "SELECT MAX(date) FROM raw.prices WHERE symbol = ?", [symbol]
    ).fetchone()
    return row[0] if row else None


def delete_prices(con: duckdb.DuckDBPyConnection, symbol: str) -> None:
    con.execute("DELETE FROM raw.prices WHERE symbol = ?", [symbol])


def upsert_prices(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insère les lignes de `df` ; une ligne (symbol, date) déjà présente est remplacée.

    Relancer la collecte plusieurs fois ne crée donc jamais de doublon.
    """
    cols = ", ".join(PRICE_COLUMNS)
    con.register("incoming", df[PRICE_COLUMNS])
    con.execute(f"INSERT OR REPLACE INTO raw.prices ({cols}) SELECT {cols} FROM incoming")
    con.unregister("incoming")
    return len(df)


def replace_trending_snapshot(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Remplace en bloc la photo des tendances des dates présentes dans `df`.

    Relancer la collecte le même jour remplace le classement du jour au lieu de
    le compléter : une cryptomonnaie sortie du classement entre-temps disparaît.
    """
    cols = ", ".join(TRENDING_COLUMNS)
    con.register("incoming", df[TRENDING_COLUMNS])
    con.execute("BEGIN")
    con.execute("DELETE FROM raw.trending WHERE snapshot_date IN (SELECT DISTINCT snapshot_date FROM incoming)")
    con.execute(f"INSERT INTO raw.trending ({cols}) SELECT {cols} FROM incoming")
    con.execute("COMMIT")
    con.unregister("incoming")
    return len(df)


def restore_trending(con: duckdb.DuckDBPyConnection, path: str) -> int:
    """Recharge un historique des tendances exporté en Parquet (dates déjà présentes : ignorées)."""
    cols = ", ".join(TRENDING_COLUMNS)
    before = con.execute("SELECT COUNT(*) FROM raw.trending").fetchone()[0]
    con.execute(
        f"""
        INSERT INTO raw.trending ({cols})
        SELECT {cols} FROM read_parquet(?)
        WHERE snapshot_date NOT IN (SELECT DISTINCT snapshot_date FROM raw.trending)
        """,
        [path],
    )
    return con.execute("SELECT COUNT(*) FROM raw.trending").fetchone()[0] - before
