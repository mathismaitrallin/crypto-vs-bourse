"""Récupération des prix journaliers depuis Yahoo Finance."""
import pandas as pd
import yfinance as yf

COLUMNS = ["date", "open", "high", "low", "close", "adj_close", "volume"]


def fetch_daily(ticker: str, start: str) -> pd.DataFrame:
    """Prix journaliers OHLCV de `ticker` depuis `start` (format AAAA-MM-JJ).

    On garde le prix brut (close) ET le prix ajusté des dividendes et splits
    (adj_close) : le premier sert au contrôle qualité, le second aux calculs
    de rendement.
    """
    hist = yf.Ticker(ticker).history(
        start=start, interval="1d", auto_adjust=False, actions=False
    )
    if hist.empty:
        return pd.DataFrame(columns=COLUMNS)

    hist = hist.reset_index()

    # On ne garde que les journées terminées : pendant la séance, Yahoo renvoie
    # une ligne du jour dont le prix bouge encore.
    today = pd.Timestamp.now(tz=hist["Date"].dt.tz).date()
    hist = hist[hist["Date"].dt.date < today]

    df = pd.DataFrame(
        {
            # Les dates Yahoo sont dans le fuseau de la place boursière :
            # on garde la date locale du jour de cotation.
            "date": hist["Date"].dt.date,
            "open": hist["Open"],
            "high": hist["High"],
            "low": hist["Low"],
            "close": hist["Close"],
            "adj_close": hist["Adj Close"] if "Adj Close" in hist else hist["Close"],
            "volume": hist["Volume"].astype(float),
        }
    )
    return df
