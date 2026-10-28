"""Simulation de portefeuilles avec rééquilibrage et frais.

Toutes les fonctions prennent des rendements SIMPLES journaliers sur le calendrier
commun (marts.fct_aligned_returns), une colonne par actif.
"""
from typing import Dict, Optional

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# Fréquences de rééquilibrage, au format des périodes pandas.
REBALANCE = {"mensuel": "M", "trimestriel": "Q", "annuel": "Y", "jamais": None}


def mix(base: Dict[str, float], extra: Dict[str, float]) -> Dict[str, float]:
    """Ajoute `extra` à un portefeuille `base` en réduisant ses lignes en proportion.

    mix({"SPY": 0.6, "TLT": 0.4}, {"BTC": 0.05}) -> SPY 57 %, TLT 38 %, BTC 5 %.
    """
    scale = 1 - sum(extra.values())
    weights = {k: v * scale for k, v in base.items()}
    for k, v in extra.items():
        weights[k] = weights.get(k, 0) + v
    return {k: v for k, v in weights.items() if v > 0}


def backtest(
    returns: pd.DataFrame,
    weights: Dict[str, float],
    rebalance: Optional[str] = "M",
    cost: float = 0.001,
) -> pd.DataFrame:
    """Valeur quotidienne d'un portefeuille (départ à 1) et poids réels de chaque actif.

    - rebalance : "M", "Q", "Y" ou None. On revient aux poids cibles à la clôture
      du dernier jour de chaque période.
    - cost : frais payés sur les montants achetés et vendus (0.001 = 0,1 %).
    """
    assets = list(weights)
    target = np.array([weights[a] for a in assets], dtype=float)
    r = returns[assets].dropna()

    periods = r.index.to_period(rebalance).to_numpy() if rebalance else None
    holdings = target.copy()
    values = np.empty(len(r))
    held_weights = np.empty((len(r), len(assets)))

    for i, daily in enumerate(r.to_numpy()):
        holdings = holdings * (1 + daily)
        total = holdings.sum()
        end_of_period = periods is not None and i + 1 < len(r) and periods[i + 1] != periods[i]
        if end_of_period:
            turnover = np.abs(total * target - holdings).sum()
            total -= turnover * cost
            holdings = total * target
        values[i] = total
        held_weights[i] = holdings / total

    out = pd.DataFrame(held_weights, index=r.index, columns=[f"poids_{a}" for a in assets])
    out.insert(0, "valeur", values)
    return out


def evaluate(values: pd.Series, risk_free: pd.Series) -> pd.Series:
    """Indicateurs d'un portefeuille à partir de sa valeur quotidienne.

    `risk_free` : rendements simples quotidiens d'un placement sans risque (ETF BIL),
    pour un ratio de Sharpe qui mesure ce que le risque rapporte EN PLUS du cash.
    """
    daily = values.pct_change().dropna()
    excess = daily - risk_free.reindex(daily.index).fillna(0)
    years = (values.index[-1] - values.index[0]).days / 365.25
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1
    max_dd = (values / values.cummax() - 1).min()
    return pd.Series(
        {
            "rendement_annuel": cagr,
            "volatilite": daily.std() * np.sqrt(TRADING_DAYS),
            "sharpe": excess.mean() / excess.std() * np.sqrt(TRADING_DAYS),
            "pire_baisse": max_dd,
            "rendement_sur_pire_baisse": cagr / abs(max_dd),
        }
    )


def risk_contribution(returns: pd.DataFrame, weights: Dict[str, float]) -> pd.Series:
    """Part du risque total (variance) apportée par chaque actif, à poids constants.

    Contribution de l'actif i = w_i × (Σw)_i / (wᵀΣw). La somme fait 100 %.
    """
    assets = list(weights)
    w = np.array([weights[a] for a in assets])
    cov = returns[assets].dropna().cov().to_numpy()
    marginal = cov @ w
    return pd.Series(w * marginal / (w @ marginal), index=assets)


def with_annual_return(returns: pd.DataFrame, symbol: str, annual_return: float) -> pd.DataFrame:
    """Copie de `returns` où `symbol` garde exactement la même volatilité et les mêmes
    mouvements jour par jour, mais avec un rendement annuel moyen imposé.

    Sert à tester « et si le Bitcoin rapportait moins à l'avenir ? » sans changer son risque.
    """
    out = returns.copy()
    logs = np.log1p(out[symbol])
    shift = np.log1p(annual_return) / TRADING_DAYS - logs.mean()
    out[symbol] = np.expm1(logs + shift)
    return out


def break_even_return(
    returns: pd.DataFrame,
    base: Dict[str, float],
    extra: Dict[str, float],
    symbol: str,
    risk_free: pd.Series,
    low: float = -0.5,
    high: float = 1.0,
) -> float:
    """Rendement annuel de `symbol` en dessous duquel l'ajouter n'améliore plus le Sharpe.

    Recherche par dichotomie : le Sharpe augmente avec le rendement de l'actif ajouté.
    """
    target = evaluate(backtest(returns, base)["valeur"], risk_free)["sharpe"]
    weights = mix(base, extra)
    for _ in range(30):
        mid = (low + high) / 2
        shifted = with_annual_return(returns, symbol, mid)
        if evaluate(backtest(shifted, weights)["valeur"], risk_free)["sharpe"] > target:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def equity_share_for_volatility(
    returns: pd.DataFrame, stocks: str, bonds: str, target_vol: float
) -> float:
    """Part d'actions d'un portefeuille actions/obligations qui atteint `target_vol`.

    Permet de comparer « ajouter de la crypto » à « simplement prendre plus d'actions »
    à risque égal, pour ne pas confondre diversification et prise de risque.
    """
    low, high = 0.0, 1.0
    for _ in range(30):
        mid = (low + high) / 2
        values = backtest(returns, {stocks: mid, bonds: 1 - mid})["valeur"]
        if values.pct_change().std() * np.sqrt(TRADING_DAYS) < target_vol:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def rolling_windows(
    returns: pd.DataFrame,
    portfolios: Dict[str, Dict[str, float]],
    risk_free: pd.Series,
    years: int = 3,
    rebalance: Optional[str] = "M",
) -> pd.DataFrame:
    """Rejoue chaque portefeuille sur toutes les fenêtres de `years` ans, une par mois de départ.

    Évite de conclure sur une seule période de départ, choisie (même sans le vouloir)
    au bon ou au mauvais moment.
    """
    rows = []
    starts = returns.index.to_series().groupby(returns.index.to_period("M")).first()
    for start in starts:
        end = start + pd.DateOffset(years=years)
        if end > returns.index[-1]:
            break
        window = returns.loc[start:end]
        for name, weights in portfolios.items():
            values = backtest(window, weights, rebalance)["valeur"]
            rows.append({"debut": start, "portefeuille": name, **evaluate(values, risk_free).to_dict()})
    return pd.DataFrame(rows)
