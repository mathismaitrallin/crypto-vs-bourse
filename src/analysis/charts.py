"""Graphiques du projet (matplotlib, images statiques pour le notebook et le README).

Règles communes : une couleur fixe par actif sur tout le projet, un seul axe
vertical par graphique, traits fins, grille discrète, légende dès deux séries
et étiquettes directes en bout de courbe.
"""
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from src.config import ROOT

FIGURES_DIR = ROOT / "reports" / "figures"

# Une couleur par actif, toujours la même (palette testée pour les daltoniens).
COLORS = {
    "SPX": "#2a78d6",
    "BTC": "#eb6834",
    "TLT": "#1baf7a",
    "GOLD": "#eda100",
    "ETH": "#e87ba4",
    "CAC": "#008300",
    "NDX": "#6250d6",
    "SOL": "#e34948",
}
# Les ETF reprennent la couleur de l'actif qu'ils représentent.
COLORS["SPY"] = COLORS["SPX"]
COLORS["GLD"] = COLORS["GOLD"]

LABELS = {
    "SPX": "S&P 500",
    "NDX": "Nasdaq",
    "CAC": "CAC 40",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "GOLD": "Or",
    "TLT": "Obligations US",
    "SPY": "Actions US",
    "GLD": "Or",
    "BIL": "Cash",
}

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BAND = "#f0efec"

SOURCE = "Sources : Binance, Yahoo Finance. Calcul : rendements journaliers sur les jours de bourse US."

plt.rcParams.update(
    {
        "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": INK_SECONDARY,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_MUTED,
        "ytick.labelcolor": INK_MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "lines.linewidth": 2,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "legend.frameon": False,
        "legend.labelcolor": INK_SECONDARY,
    }
)


# --- Mise en page ---------------------------------------------------------------

def _figure(title: str, subtitle: str, size: Tuple[float, float] = (10, 5.4)):
    fig, ax = plt.subplots(figsize=size)
    fig.subplots_adjust(left=0.07, right=0.86, top=0.80, bottom=0.14)
    fig.text(0.07, 0.94, title, fontsize=15, fontweight="semibold", color=INK)
    fig.text(0.07, 0.885, subtitle, fontsize=10.5, color=INK_SECONDARY)
    fig.text(0.07, 0.025, SOURCE, fontsize=8, color=INK_MUTED)
    ax.tick_params(length=0, pad=6)
    ax.set_axisbelow(True)
    return fig, ax


def _legend(ax, symbols: Sequence[str], ncol: Optional[int] = None) -> None:
    handles = [plt.Line2D([], [], color=COLORS[s], lw=2) for s in symbols]
    ax.legend(
        handles, [LABELS[s] for s in symbols],
        loc="lower left", bbox_to_anchor=(0, 1.0), ncol=ncol or len(symbols),
        handlelength=1.4, columnspacing=1.6, borderaxespad=0.3,
    )


def _end_labels(ax, items: List[Tuple[pd.Timestamp, float, str, str]], min_gap_px: float = 15) -> None:
    """Point et étiquette en bout de courbe ; les étiquettes trop proches sont
    écartées verticalement et reliées à leur courbe par un fin trait."""
    fig = ax.figure
    fig.canvas.draw()
    to_px = ax.transData
    to_data = ax.transData.inverted()

    points = []
    for x, y, text, color in items:
        x = mdates.date2num(pd.Timestamp(x))
        px = to_px.transform((x, y))
        points.append([px[0], px[1], px[1], text, color, x, y])
    points.sort(key=lambda p: p[2])
    for i in range(1, len(points)):
        if points[i][2] - points[i - 1][2] < min_gap_px:
            points[i][2] = points[i - 1][2] + min_gap_px

    for px_x, px_y, label_y, text, color, x, y in points:
        ax.plot([x], [y], marker="o", ms=8, color=color, mec=SURFACE, mew=2, zorder=5, clip_on=False)
        lx, ly = to_data.transform((px_x + 14, label_y))
        if abs(label_y - px_y) > 1:
            ax.plot([x, lx], [y, ly], color=BASELINE, lw=0.8, clip_on=False, zorder=4)
        ax.text(lx, ly, f" {text}", va="center", ha="left", fontsize=9.5, color=INK_SECONDARY, clip_on=False)


def fr(value: float, decimals: int = 2) -> str:
    """Nombre au format français : virgule décimale, vrai signe moins."""
    return f"{value:.{decimals}f}".replace(".", ",").replace("-", "−")


def fr_pct(value: float) -> str:
    return f"{value:.0%}".replace("-", "−").replace("%", " %")


def _nice_ticks(ax, axis: str = "y") -> None:
    """Graduations sur des valeurs rondes (1, 2, 5, 10...), jamais 2,5 : une graduation
    affichée avec peu de décimales doit tomber pile sur la valeur qu'elle annonce."""
    locator = mticker.MaxNLocator(nbins=6, steps=[1, 2, 5, 10])
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_locator(locator)


def _percent_axis(ax, axis: str = "y") -> None:
    fmt = mticker.FuncFormatter(lambda v, _: fr_pct(v))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)
    _nice_ticks(ax, axis)


def _correlation_axis(ax, axis: str = "y") -> None:
    fmt = mticker.FuncFormatter(lambda v, _: fr(v, 1))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)
    _nice_ticks(ax, axis)


def save(fig, name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=200)
    return path


# --- Graphiques -------------------------------------------------------------------

def growth_of_100(prices: pd.DataFrame, symbols: Sequence[str]):
    """Valeur de 100 $ investis au départ, échelle logarithmique."""
    data = prices[list(symbols)].dropna()
    index = data / data.iloc[0] * 100

    fig, ax = _figure(
        "Ce que sont devenus 100 $ investis début 2018",
        "Échelle logarithmique : une même distance verticale représente une même variation en %",
    )
    for s in symbols:
        ax.plot(index.index, index[s], color=COLORS[s])
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mticker.FixedLocator([25, 50, 100, 200, 400, 800, 1600]))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f} $".replace(",", " ")))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlim(index.index[0], index.index[-1])
    _legend(ax, symbols)
    last = index.iloc[-1]
    _end_labels(ax, [(index.index[-1], last[s], f"{last[s]:.0f} $", COLORS[s]) for s in symbols])
    return fig


def drawdowns(prices: pd.DataFrame, symbols: Sequence[str]):
    """Baisse depuis le plus haut historique, pour chaque actif."""
    data = prices[list(symbols)].dropna()
    dd = data / data.cummax() - 1

    fig, ax = _figure(
        "Les chutes depuis le plus haut historique",
        "0 % = l'actif est à son record ; -50 % = il a perdu la moitié de sa valeur depuis",
    )
    for s in symbols:
        ax.fill_between(dd.index, dd[s], 0, color=COLORS[s], alpha=0.10, lw=0)
        ax.plot(dd.index, dd[s], color=COLORS[s])
    ax.set_ylim(-1, 0.02)
    ax.set_xlim(dd.index[0], dd.index[-1])
    _percent_axis(ax)
    ax.axhline(0, color=BASELINE, lw=1)
    _legend(ax, symbols)
    last = dd.iloc[-1]
    _end_labels(ax, [(dd.index[-1], last[s], fr_pct(last[s]), COLORS[s]) for s in symbols])
    return fig


def rolling_volatility(vols: pd.DataFrame, ratio: pd.Series):
    """Volatilité annualisée glissante de plusieurs actifs, sur un même axe."""
    data = vols.dropna()
    symbols = list(data.columns)

    fig, ax = _figure(
        "Le Bitcoin est de moins en moins volatil… mais reste à part",
        f"Volatilité annualisée sur 1 an glissant. Aujourd'hui, le Bitcoin est {fr(ratio.dropna().iloc[-1], 1)} fois "
        f"plus volatil que le Nasdaq (contre {fr(ratio.dropna().iloc[0], 1)} fois fin 2018)",
    )
    for s in symbols:
        ax.plot(data.index, data[s], color=COLORS[s])
    ax.set_ylim(0, None)
    ax.set_xlim(data.index[0], data.index[-1])
    _percent_axis(ax)
    ax.axhline(0, color=BASELINE, lw=1)
    _legend(ax, symbols)
    last = data.iloc[-1]
    _end_labels(ax, [(data.index[-1], last[s], fr_pct(last[s]), COLORS[s]) for s in symbols])
    return fig


def yearly_correlation(corr: pd.DataFrame, highlight: str):
    """Corrélation annuelle du Bitcoin avec plusieurs actifs (colonnes = contreparties)."""
    symbols = list(corr.columns)
    years = corr.index.astype(int)
    x = np.arange(len(years))
    width = 0.32

    fig, ax = _figure(
        "Depuis 2020, le Bitcoin bouge en partie avec la bourse américaine",
        "Corrélation des rendements journaliers du Bitcoin, année par année "
        "(0 = aucun lien, 1 = mouvements identiques)",
    )
    for i, s in enumerate(symbols):
        offset = (i - (len(symbols) - 1) / 2) * (width + 0.03)
        bars = ax.bar(x + offset, corr[s], width=width, color=COLORS[s], lw=0)
        if s == highlight:
            for rect, v in zip(bars, corr[s]):
                va, dy = ("bottom", 3) if v >= 0 else ("top", -3)
                ax.annotate(fr(v), (rect.get_x() + rect.get_width() / 2, v), xytext=(0, dy),
                            textcoords="offset points", ha="center", va=va, fontsize=8.5, color=INK_SECONDARY)
    ax.axhline(0, color=BASELINE, lw=1)
    ax.set_xticks(x, [str(y) + (" *" if y == years.max() else "") for y in years])
    ax.set_ylim(-0.3, 0.8)
    _correlation_axis(ax)
    ax.text(1.0, -0.12, "* année en cours", transform=ax.transAxes, ha="right", fontsize=8, color=INK_MUTED)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[s]) for s in symbols]
    ax.legend(handles, [f"Bitcoin et {LABELS[s]}" for s in symbols], loc="lower left",
              bbox_to_anchor=(0, 1.0), ncol=len(symbols), handlelength=1, columnspacing=1.6, borderaxespad=0.3)
    return fig


def rolling_correlation(corr: pd.Series, pair: Tuple[str, str], crises: pd.DataFrame, window_label: str):
    """Corrélation glissante d'une paire, avec les krachs boursiers en bandes grises."""
    a, b = pair
    data = corr.dropna()

    fig, ax = _figure(
        f"Corrélation {LABELS[a]} / {LABELS[b]} au fil du temps",
        f"Sur {window_label} glissants. Bandes grises : baisses de plus de 10 % du S&P 500 (du sommet au point bas)",
    )
    # Un krach terminé avant le début de la courbe (fenêtre glissante) n'est pas affiché.
    for _, c in crises[crises["point_bas"] >= data.index[0]].iterrows():
        ax.axvspan(c["sommet"], c["point_bas"], color=BAND, lw=0, zorder=0)
        ax.text(c["sommet"], 0.97, c["nom"], transform=ax.get_xaxis_transform(), fontsize=8.5,
                color=INK_SECONDARY, va="top", ha="left")
    ax.plot(data.index, data, color=COLORS[b])
    ax.axhline(0, color=BASELINE, lw=1)
    ax.set_ylim(-0.5, 1)
    ax.set_xlim(data.index[0], data.index[-1])
    _correlation_axis(ax)
    _end_labels(ax, [(data.index[-1], data.iloc[-1], fr(data.iloc[-1]), COLORS[b])])
    return fig


def conditional_correlation(table: pd.DataFrame, reference: str):
    """Corrélation avec `reference` les jours de forte baisse et de forte hausse.

    `table` : une ligne par actif, colonnes « baisse » et « hausse ».
    """
    symbols = list(table.index)
    y = np.arange(len(symbols))[::-1]

    fig, ax = _figure(
        f"Quand le {LABELS[reference]} chute, le Bitcoin chute avec lui",
        f"Corrélation avec le {LABELS[reference]}, les jours où il baisse de plus de 1 % "
        "et ceux où il monte de plus de 1 %",
        size=(10, 4.6),
    )
    fig.subplots_adjust(left=0.15)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    for yi, s in zip(y, symbols):
        down, up = table.loc[s, "baisse"], table.loc[s, "hausse"]
        ax.plot([up, down], [yi, yi], color=BASELINE, lw=2, zorder=1)
        ax.plot([up], [yi], marker="o", ms=10, color=BASELINE, mec=SURFACE, mew=2, zorder=2)
        ax.plot([down], [yi], marker="o", ms=10, color=INK, mec=SURFACE, mew=2, zorder=3)
        ax.annotate(fr(down), (down, yi), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK_SECONDARY)
    ax.axvline(0, color=BASELINE, lw=1)
    ax.set_yticks(y, [LABELS[s] for s in symbols], color=INK_SECONDARY, fontsize=10)
    ax.set_xlim(-0.4, 1)
    _correlation_axis(ax, "x")
    ax.set_ylim(-0.6, len(symbols) - 0.4)
    handles = [
        plt.Line2D([], [], marker="o", ls="", ms=9, color=INK),
        plt.Line2D([], [], marker="o", ls="", ms=9, color=BASELINE),
    ]
    ax.legend(handles, [f"Jours de baisse du {LABELS[reference]}", f"Jours de hausse du {LABELS[reference]}"],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, columnspacing=1.6, borderaxespad=0.3)
    return fig


def crisis_performance(table: pd.DataFrame, highlight: str):
    """Variation de chaque actif pendant chaque krach (lignes = krachs, colonnes = actifs)."""
    symbols = list(table.columns)
    x = np.arange(len(table))
    width = 0.15

    fig, ax = _figure(
        "Pendant les krachs boursiers, le Bitcoin n'a jamais protégé",
        "Variation de chaque actif entre le sommet et le point bas du S&P 500, pour chaque baisse de plus de 10 %",
    )
    for i, s in enumerate(symbols):
        offset = (i - (len(symbols) - 1) / 2) * (width + 0.02)
        bars = ax.bar(x + offset, table[s], width=width, color=COLORS[s], lw=0)
        if s == highlight:
            for rect, v in zip(bars, table[s]):
                ax.annotate(fr_pct(v), (rect.get_x() + rect.get_width() / 2, v), xytext=(0, -3),
                            textcoords="offset points", ha="center", va="top", fontsize=8.5, color=INK_SECONDARY)
    ax.axhline(0, color=BASELINE, lw=1)
    ax.set_xticks(x, table.index, color=INK_SECONDARY)
    ax.set_ylim(-0.75, 0.25)
    _percent_axis(ax)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[s]) for s in symbols]
    ax.legend(handles, [LABELS[s] for s in symbols], loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=len(symbols), handlelength=1, columnspacing=1.6, borderaxespad=0.3)
    return fig


# --- Graphiques portefeuille ------------------------------------------------------

# Portefeuille de référence (sans crypto) : gris neutre, la crypto garde sa couleur.
REFERENCE = INK_MUTED


def allocation_curves(table: pd.DataFrame, highlight: float = 0.05):
    """Indicateurs du portefeuille selon la part de Bitcoin (index = part, de 0 à 1).

    Trois petits graphiques côte à côte plutôt qu'un graphique à deux axes.
    """
    panels = [
        ("rendement_annuel", "Rendement annuel", fr_pct_1),
        ("sharpe", "Ratio de Sharpe", lambda v: fr(v, 2)),
        ("pire_baisse", "Pire baisse", fr_pct),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.6))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.72, bottom=0.17, wspace=0.35)
    fig.text(0.07, 0.93, "Plus de Bitcoin : plus de rendement, mais des chutes plus profondes",
             fontsize=15, fontweight="semibold", color=INK)
    fig.text(0.07, 0.865, "Portefeuille 60 % actions / 40 % obligations, dans lequel on remplace une part par du Bitcoin "
             "(rééquilibrage mensuel)", fontsize=10.5, color=INK_SECONDARY)
    fig.text(0.07, 0.025, SOURCE, fontsize=8, color=INK_MUTED)

    x = table.index.to_numpy()
    for ax, (col, title, fmt) in zip(axes, panels):
        y = table[col].to_numpy()
        ax.plot(x, y, color=COLORS["BTC"])
        ax.plot(x, y, "o", ms=6, color=COLORS["BTC"], mec=SURFACE, mew=1.5)
        ax.set_title(title, loc="left", fontsize=11, color=INK, pad=10)
        ax.tick_params(length=0, pad=6)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fr_pct(v)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _, f=fmt: f(v)))
        _nice_ticks(ax)
        ax.set_xlabel("Part de Bitcoin", color=INK_MUTED, fontsize=9)
        # Étiquettes placées du côté opposé à la courbe pour ne jamais la chevaucher.
        rising = y[-1] > y[0]
        placements = [
            (x[0], (0, -16) if rising else (0, 10), "center"),
            (highlight, (-8, 6) if rising else (8, 6), "right" if rising else "left"),
            (x[-1], (0, 10) if rising else (0, -16), "center"),
        ]
        for xi, offset, ha in placements:
            yi = table.loc[xi, col]
            ax.annotate(fmt(yi), (xi, yi), xytext=offset, textcoords="offset points",
                        ha=ha, va="center", fontsize=8.5, color=INK_SECONDARY)
        lo, hi = y.min(), y.max()
        pad = (hi - lo) * 0.3
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlim(x[0] - 0.02, x[-1] + 0.02)
    return fig


def fr_pct_1(value: float) -> str:
    return f"{value:.1%}".replace(".", ",").replace("-", "−").replace("%", " %")


def portfolio_growth(values: pd.DataFrame, colors: Dict[str, str]):
    """Valeur de 100 investis dans chaque portefeuille (colonnes = portefeuilles)."""
    data = values / values.iloc[0] * 100

    fig, ax = _figure(
        "100 $ placés début 2018 dans chaque portefeuille",
        "Rééquilibrage mensuel, frais de 0,1 % sur chaque achat et vente",
    )
    for name in data.columns:
        ax.plot(data.index, data[name], color=colors[name])
    ax.set_xlim(data.index[0], data.index[-1])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f} $"))
    handles = [plt.Line2D([], [], color=colors[n], lw=2) for n in data.columns]
    ax.legend(handles, list(data.columns), loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=len(data.columns), handlelength=1.4, columnspacing=1.6, borderaxespad=0.3)
    last = data.iloc[-1]
    _end_labels(ax, [(data.index[-1], last[n], f"{last[n]:.0f} $", colors[n]) for n in data.columns])
    return fig


def capital_vs_risk(capital: pd.Series, risk: pd.Series):
    """Deux barres empilées : répartition du capital et répartition du risque."""
    symbols = list(capital.index)
    rows = [("Part du capital", capital), ("Part du risque", risk)]

    crypto = symbols[-1]
    composition = ", ".join(f"{fr_pct(capital[s])} {LABELS[s]}" for s in symbols)
    fig, ax = _figure(
        f"{fr_pct(capital[crypto])} du capital, mais {fr_pct(risk[crypto])} du risque",
        f"Portefeuille {composition} : contribution de chaque ligne à la volatilité totale",
        size=(10, 4.4),
    )
    fig.subplots_adjust(left=0.17, top=0.70, bottom=0.18)
    ax.grid(False)
    y = np.array([1, 0])
    for yi, (_, shares) in zip(y, rows):
        left = 0.0
        for s in symbols:
            width = shares[s]
            ax.barh(yi, width, left=left, height=0.5, color=COLORS[s], edgecolor=SURFACE, linewidth=2)
            label = fr_pct(width)
            if width >= 0.08:
                ax.text(left + width / 2, yi, label, ha="center", va="center", fontsize=9.5,
                        color="white" if s != "TLT" else INK)
            else:
                ax.text(left + width + 0.01, yi, label, ha="left", va="center", fontsize=9.5,
                        color=INK_SECONDARY)
            left += width
    ax.set_yticks(y, [name for name, _ in rows], color=INK_SECONDARY, fontsize=10)
    ax.set_xlim(0, 1.08)
    ax.set_xticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[s]) for s in symbols]
    ax.legend(handles, [LABELS[s] for s in symbols], loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=len(symbols), handlelength=1, columnspacing=1.6, borderaxespad=0.3)
    return fig


def weight_drift(weights: pd.DataFrame, colors: Dict[str, str], target: float):
    """Poids réel du Bitcoin dans le portefeuille selon la politique de rééquilibrage."""
    fig, ax = _figure(
        "Sans rééquilibrage, le Bitcoin prend vite trop de place",
        f"Part réelle du Bitcoin dans le portefeuille, pour une cible de {fr_pct(target)}",
    )
    for name in weights.columns:
        ax.plot(weights.index, weights[name], color=colors[name], lw=2)
    ax.set_xlim(weights.index[0], weights.index[-1])
    ax.set_ylim(0, None)
    _percent_axis(ax)
    ax.axhline(0, color=BASELINE, lw=1)
    handles = [plt.Line2D([], [], color=colors[n], lw=2) for n in weights.columns]
    ax.legend(handles, list(weights.columns), loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=len(weights.columns), handlelength=1.4, columnspacing=1.6, borderaxespad=0.3)
    peak_name = weights.max().idxmax()
    peak_date = weights[peak_name].idxmax()
    peak = weights[peak_name].max()
    ax.annotate(f"jusqu'à {fr_pct(peak)}", (peak_date, peak), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9, color=INK_SECONDARY)
    return fig


def return_sensitivity(table: pd.Series, reference: float, actual: float, break_even: float):
    """Sharpe du portefeuille avec Bitcoin selon le rendement annuel supposé du Bitcoin."""
    fig, ax = _figure(
        "Et si le Bitcoin rapportait moins à l'avenir ?",
        "Ratio de Sharpe du portefeuille avec 5 % de Bitcoin, en gardant ses variations passées "
        "mais en changeant son rendement moyen",
    )
    x = table.index.to_numpy()
    ax.plot(x, table.to_numpy(), color=COLORS["BTC"])
    ax.axhline(reference, color=REFERENCE, lw=1.5)
    ax.text(x[0], reference, "  Sharpe du 60/40 sans Bitcoin", va="bottom", ha="left", fontsize=9, color=INK_SECONDARY)
    ax.plot([break_even], [reference], "o", ms=8, color=INK, mec=SURFACE, mew=2, zorder=5)
    ax.annotate(f"Seuil : {fr_pct(break_even)} par an", (break_even, reference), xytext=(10, -10),
                textcoords="offset points", ha="left", va="top", fontsize=9, color=INK_SECONDARY)
    actual_sharpe = float(np.interp(actual, x, table.to_numpy()))
    ax.plot([actual], [actual_sharpe], "o", ms=8, color=COLORS["BTC"], mec=SURFACE, mew=2, zorder=5)
    ax.annotate(f"Rendement réel 2018-2026 : {fr_pct(actual)} par an", (actual, actual_sharpe), xytext=(-8, 8),
                textcoords="offset points", ha="right", va="bottom", fontsize=9, color=INK_SECONDARY)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fr_pct(v)))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: fr(v, 2)))
    _nice_ticks(ax)
    ax.set_xlabel("Rendement annuel moyen supposé du Bitcoin", color=INK_MUTED, fontsize=9)
    ax.set_xlim(x[0], x[-1])
    return fig


def rolling_sharpe(table: pd.DataFrame, colors: Dict[str, str], years: int):
    """Sharpe de chaque portefeuille sur des fenêtres glissantes (index = date de départ)."""
    fig, ax = _figure(
        f"Sur chaque période de {years} ans testée, le Bitcoin a amélioré le Sharpe",
        f"Ratio de Sharpe sur {years} ans, selon le mois de départ de l'investissement",
    )
    for name in table.columns:
        ax.plot(table.index, table[name], color=colors[name])
    ax.axhline(0, color=BASELINE, lw=1)
    ax.set_xlim(table.index[0], table.index[-1])
    _correlation_axis(ax)
    ax.set_xlabel("Mois de départ", color=INK_MUTED, fontsize=9)
    handles = [plt.Line2D([], [], color=colors[n], lw=2) for n in table.columns]
    ax.legend(handles, list(table.columns), loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=len(table.columns), handlelength=1.4, columnspacing=1.6, borderaxespad=0.3)
    return fig
