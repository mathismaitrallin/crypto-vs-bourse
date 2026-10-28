"""Chargement des tables d'analyse (construites par dbt) en DataFrames pandas.

Deux sources possibles, dans cet ordre :
1. la base DuckDB locale (data/market.duckdb), quand on travaille sur le projet ;
2. l'export Parquet des tables finales, local (data/export) ou distant (variable
   d'environnement DATA_URL), utilisé par le dashboard en ligne qui n'a pas la base.
"""
import os

import pandas as pd

from src.config import DB_PATH, ROOT

EXPORT_DIR = ROOT / "data" / "export"
TABLES = ["dim_assets", "fct_daily_returns", "fct_aligned_returns", "fct_trending"]


def load_table(name: str) -> pd.DataFrame:
    if DB_PATH.exists():
        from src.db import connect  # import tardif : le dashboard n'a pas besoin de DuckDB

        con = connect(read_only=True)
        try:
            return con.sql(f"select * from marts.{name}").df()
        finally:
            con.close()
    source = os.environ.get("DATA_URL", str(EXPORT_DIR)).rstrip("/")
    return pd.read_parquet(f"{source}/{name}.parquet")


def _wide(table: str, value: str) -> pd.DataFrame:
    df = load_table(table)
    wide = df.pivot(index="date", columns="symbol", values=value)
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def load_assets() -> pd.DataFrame:
    """Référentiel des actifs, indexé par symbole."""
    return load_table("dim_assets").set_index("symbol")


def load_aligned(value: str = "log_return") -> pd.DataFrame:
    """Une colonne par actif, une ligne par jour de bourse US.

    `value` : log_return, simple_return ou price.
    À utiliser pour comparer des actifs entre eux.
    """
    return _wide("fct_aligned_returns", value)


def load_native(value: str = "log_return") -> pd.DataFrame:
    """Une colonne par actif, sur le calendrier propre à chaque actif.

    Les week-ends sont vides (NaN) pour les actifs non crypto : utiliser
    `.dropna()` colonne par colonne. À utiliser pour étudier un actif seul.
    """
    return _wide("fct_daily_returns", value)
