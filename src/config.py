"""Configuration centrale : actifs suivis, période d'historique, chemins."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "market.duckdb"

# Historique des cryptomonnaies tendance. CoinGecko ne donne que le classement du moment :
# en ligne, la base est reconstruite chaque jour, donc le workflow récupère ici l'historique
# publié la veille (branche data) avant d'y ajouter la photo du jour.
TRENDING_HISTORY_PATH = ROOT / "data" / "history" / "raw_trending.parquet"

# Début de l'historique. Binance n'a des données BTC qu'à partir d'août 2017.
START_DATE = "2018-01-01"

# À chaque mise à jour, on re-télécharge les N derniers jours pour écraser
# une éventuelle bougie incomplète ou une correction côté source.
LOOKBACK_DAYS = 5


@dataclass(frozen=True)
class Asset:
    symbol: str          # identifiant interne, utilisé partout dans la base
    name: str
    asset_class: str     # crypto | action | obligation | matiere_premiere | monetaire
    source: str          # binance | yahoo
    source_ticker: str   # ticker tel que l'API source l'attend


ASSETS = [
    # Crypto (Binance, cotées en USDT, 24h/24 7j/7)
    Asset("BTC", "Bitcoin", "crypto", "binance", "BTCUSDT"),
    Asset("ETH", "Ethereum", "crypto", "binance", "ETHUSDT"),
    Asset("SOL", "Solana", "crypto", "binance", "SOLUSDT"),
    # Marchés traditionnels (Yahoo Finance, jours de bourse uniquement)
    Asset("SPX", "S&P 500", "action", "yahoo", "^GSPC"),
    Asset("NDX", "Nasdaq Composite", "action", "yahoo", "^IXIC"),
    Asset("CAC", "CAC 40", "action", "yahoo", "^FCHI"),
    Asset("TLT", "Obligations US 20 ans+ (ETF)", "obligation", "yahoo", "TLT"),
    Asset("GOLD", "Or (contrat future)", "matiere_premiere", "yahoo", "GC=F"),
    # ETF réellement achetables, dividendes réinvestis : base des simulations de portefeuille.
    # (L'indice ^GSPC ci-dessus n'inclut pas les dividendes.)
    Asset("SPY", "S&P 500 (ETF SPY)", "action", "yahoo", "SPY"),
    Asset("GLD", "Or (ETF GLD)", "matiere_premiere", "yahoo", "GLD"),
    Asset("BIL", "Bons du Trésor US 1-3 mois (ETF BIL)", "monetaire", "yahoo", "BIL"),
]
