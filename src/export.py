"""Export des tables finales en Parquet, pour le dashboard en ligne.

Exporte aussi l'historique brut des tendances (raw_trending.parquet) : le workflow
le récupère le lendemain pour y ajouter la nouvelle photo, sans rien perdre.

Usage :
    python -m src.export
"""
from src.analysis.data import EXPORT_DIR, TABLES
from src.config import TRENDING_HISTORY_PATH
from src.db import connect


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    for table in TABLES:
        path = EXPORT_DIR / f"{table}.parquet"
        con.execute(f"COPY marts.{table} TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
        print(f"  ✓ {table:<20} → {path.relative_to(EXPORT_DIR.parents[1])} ({path.stat().st_size / 1024:.0f} Ko)")
    history = EXPORT_DIR / TRENDING_HISTORY_PATH.name
    con.execute(f"COPY raw.trending TO '{history}' (FORMAT parquet, COMPRESSION zstd)")
    print(f"  ✓ {'raw.trending':<20} → {history.relative_to(EXPORT_DIR.parents[1])} (historique)")
    con.close()


if __name__ == "__main__":
    main()
