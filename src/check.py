"""Contrôle rapide du contenu de la base, actif par actif.

Usage :
    python -m src.check
"""
from src.db import connect

SUMMARY_SQL = """
SELECT
    a.symbol,
    a.asset_class                                         AS classe,
    MIN(p.date)                                           AS premiere_date,
    MAX(p.date)                                           AS derniere_date,
    COUNT(p.date)                                         AS nb_lignes,
    -- Part des jours calendaires couverts : ~100 % pour la crypto (7j/7),
    -- ~70 % pour la bourse (pas de cotation le week-end ni les jours fériés).
    ROUND(100.0 * COUNT(p.date)
          / (DATE_DIFF('day', MIN(p.date), MAX(p.date)) + 1), 1) AS pct_jours_couverts,
    COUNT(*) FILTER (WHERE p.close IS NULL)               AS prix_manquants,
    COUNT(*) FILTER (WHERE p.high < p.low OR p.close <= 0
                     OR p.close > p.high OR p.close < p.low) AS lignes_incoherentes,
    ROUND(ARG_MAX(p.close, p.date), 2)                    AS dernier_prix
FROM raw.assets a
LEFT JOIN raw.prices p USING (symbol)
GROUP BY ALL
ORDER BY classe, a.symbol
"""


def main() -> None:
    con = connect(read_only=True)
    con.sql(SUMMARY_SQL).show(max_width=200)
    con.close()


if __name__ == "__main__":
    main()
