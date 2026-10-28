"""Indicateurs de performance, de risque et de dépendance entre actifs.

Toutes les fonctions prennent des rendements logarithmiques journaliers
(ou des prix pour les drawdowns) et ne font aucun accès à la base.
"""
from typing import Dict, Tuple

import numpy as np
import pandas as pd


# --- Performance et risque ----------------------------------------------------

def annualized_return(log_returns: pd.Series, periods_per_year: int) -> float:
    """Rendement annuel moyen composé (équivalent à un taux annuel constant)."""
    return float(np.exp(log_returns.mean() * periods_per_year) - 1)


def annualized_volatility(log_returns: pd.Series, periods_per_year: int) -> float:
    return float(log_returns.std() * np.sqrt(periods_per_year))


def sharpe_ratio(log_returns: pd.Series, periods_per_year: int) -> float:
    """Rendement par unité de risque. Taux sans risque pris à 0 par simplicité."""
    simple = np.expm1(log_returns)
    return float(simple.mean() / simple.std() * np.sqrt(periods_per_year))


def drawdown(prices: pd.Series) -> pd.Series:
    """Baisse par rapport au plus haut historique atteint jusque-là (0 = au sommet)."""
    return prices / prices.cummax() - 1


def summary_table(native_returns: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    """Tableau performance / risque, chaque actif sur son propre calendrier."""
    rows = []
    for symbol in native_returns.columns:
        r = native_returns[symbol].dropna()
        periods = int(assets.loc[symbol, "periods_per_year"])
        prices = np.exp(r.cumsum())
        rows.append(
            {
                "symbol": symbol,
                "classe": assets.loc[symbol, "asset_class"],
                "depuis": r.index.min().date(),
                "rendement_annuel": annualized_return(r, periods),
                "volatilite_annuelle": annualized_volatility(r, periods),
                "sharpe": sharpe_ratio(r, periods),
                "pire_baisse": drawdown(prices).min(),
                "pire_jour": float(np.expm1(r.min())),
            }
        )
    return pd.DataFrame(rows).set_index("symbol")


# --- Dépendance entre actifs ----------------------------------------------------

def rolling_correlation(returns: pd.DataFrame, a: str, b: str, window: int) -> pd.Series:
    return returns[a].rolling(window).corr(returns[b])


def rolling_volatility(returns: pd.DataFrame, symbol: str, window: int, periods_per_year: int = 252) -> pd.Series:
    return returns[symbol].rolling(window).std() * np.sqrt(periods_per_year)


def correlation_by_period(
    returns: pd.DataFrame, periods: Dict[str, Tuple[str, str]]
) -> Dict[str, pd.DataFrame]:
    """Matrice de corrélation pour chaque période {nom: (début, fin)}."""
    return {name: returns.loc[start:end].corr() for name, (start, end) in periods.items()}


def yearly_correlation(returns: pd.DataFrame, a: str, b: str) -> pd.Series:
    pair = returns[[a, b]].dropna()
    return pair.groupby(pair.index.year).apply(lambda g: g[a].corr(g[b]))


def conditional_correlation(
    returns: pd.DataFrame, a: str, b: str, threshold: float = 0.01
) -> pd.Series:
    """Corrélation de `a` avec `b` selon que `b` monte ou baisse fortement.

    Une corrélation plus forte les jours de baisse signifie que `a` chute
    avec `b` quand ça va mal, mais ne monte pas autant avec lui quand ça va bien :
    c'est le contraire d'une protection.
    """
    pair = returns[[a, b]].dropna()
    move = np.expm1(pair[b])
    return pd.Series(
        {
            f"jours où {b} baisse de plus de {threshold:.0%}": pair[move < -threshold].corr().iloc[0, 1],
            "tous les jours": pair.corr().iloc[0, 1],
            f"jours où {b} monte de plus de {threshold:.0%}": pair[move > threshold].corr().iloc[0, 1],
        }
    )


# --- Crises ---------------------------------------------------------------------

def drawdown_episodes(prices: pd.Series, threshold: float = -0.10) -> pd.DataFrame:
    """Épisodes de baisse d'au moins `threshold` depuis un sommet.

    Chaque épisode va du sommet (peak) au point bas (trough), puis jusqu'au
    retour au sommet (recovery, vide si pas encore revenu).
    """
    dd = drawdown(prices)
    episodes = []
    peak_date = prices.index[0]
    in_drawdown = False

    for day, value in dd.items():
        if value == 0:
            if in_drawdown:
                episodes.append((peak_date, day))
                in_drawdown = False
            peak_date = day
        else:
            in_drawdown = True
    if in_drawdown:
        episodes.append((peak_date, None))

    rows = []
    for peak, recovery in episodes:
        window = dd.loc[peak:recovery] if recovery is not None else dd.loc[peak:]
        trough = window.idxmin()
        if window.min() <= threshold:
            rows.append(
                {
                    "sommet": peak,
                    "point_bas": trough,
                    "retour_au_sommet": recovery,
                    "baisse": window.min(),
                    "jours_de_baisse": (trough - peak).days,
                }
            )
    return pd.DataFrame(rows)


def performance_during(prices: pd.DataFrame, start, end) -> pd.Series:
    """Variation de chaque actif entre deux dates."""
    window = prices.loc[start:end]
    return window.iloc[-1] / window.iloc[0] - 1
