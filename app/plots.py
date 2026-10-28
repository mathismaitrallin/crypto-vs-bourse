"""Graphiques interactifs (Plotly) du dashboard.

Mêmes règles que les graphiques statiques du projet (src/analysis/charts.py) :
une couleur fixe par actif, un seul axe vertical, traits fins, grille discrète,
légende dès deux séries. En plus : survol avec la valeur de chaque série.
"""
from typing import Dict, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

from langue import langue, pct

# Couleurs et noms repris tels quels des graphiques statiques (sans importer
# matplotlib dans le dashboard).
COLORS = {
    "SPX": "#2a78d6", "SPY": "#2a78d6",
    "BTC": "#eb6834",
    "TLT": "#1baf7a",
    "GOLD": "#eda100", "GLD": "#eda100",
    "ETH": "#e87ba4",
    "CAC": "#008300",
    "NDX": "#6250d6",
    "SOL": "#e34948",
}
_LABELS = {
    "fr": {
        "SPX": "S&P 500", "NDX": "Nasdaq", "CAC": "CAC 40",
        "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana",
        "GOLD": "Or", "TLT": "Obligations US",
        "SPY": "Actions US", "GLD": "Or", "BIL": "Cash",
    },
    "en": {
        "SPX": "S&P 500", "NDX": "Nasdaq", "CAC": "CAC 40",
        "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana",
        "GOLD": "Gold", "TLT": "US Treasuries",
        "SPY": "US stocks", "GLD": "Gold", "BIL": "Cash",
    },
}


def asset_labels() -> Dict[str, str]:
    """Noms des actifs dans la langue du visiteur."""
    return _LABELS[langue()]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BAND = "#f0efec"
REFERENCE = INK_MUTED

FORMATS = {"pct": ".0%", "pct1": ".1%", "num": ".2f", "num1": ".1f", "money": ",.0f"}



def _unit(y_format: str) -> Tuple[str, str]:
    """Texte avant / après chaque valeur (graduations et survol) : 100 $ / $100."""
    if y_format != "money":
        return "", ""
    return ("$", "") if langue() == "en" else ("", " $")


def _layout(
    fig: go.Figure, y_format: str, height: int = 420, log: bool = False, y_title: Optional[str] = None
) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK_SECONDARY, size=13),
        separators=".," if langue() == "en" else ", ",  # FR : virgule décimale, espace pour les milliers
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK)),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", xanchor="left", title=None),
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, ticks="", tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(
        gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=SURFACE, ticks="",
        tickfont=dict(color=INK_MUTED), tickformat=FORMATS[y_format],
        tickprefix=_unit(y_format)[0], ticksuffix=_unit(y_format)[1],
        type="log" if log else "linear",
        title=dict(text=y_title, font=dict(size=12, color=INK_MUTED)) if y_title else None,
    )
    return fig


def lines(
    df: pd.DataFrame,
    y_format: str = "pct",
    colors: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    log: bool = False,
    fill: bool = False,
    bands: Optional[pd.DataFrame] = None,
    reference: Optional[float] = None,
    height: int = 420,
    y_title: Optional[str] = None,
) -> go.Figure:
    """Une courbe par colonne. `bands` : périodes à griser (colonnes sommet, point_bas, nom)."""
    colors = colors or COLORS
    labels = labels or asset_labels()
    prefix, suffix = _unit(y_format)
    fig = go.Figure()
    if bands is not None:
        for _, b in bands.iterrows():
            fig.add_vrect(x0=b["sommet"], x1=b["point_bas"], fillcolor=BAND, line_width=0, layer="below",
                          annotation_text=b.get("nom", ""), annotation_position="top left",
                          annotation_font=dict(size=11, color=INK_SECONDARY))
    for col in df.columns:
        color = colors.get(col, INK_SECONDARY)
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[col], name=labels.get(col, col), mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy" if fill else None,
                fillcolor=_wash(color) if fill else None,
                hovertemplate=f"{prefix}%{{y:{FORMATS[y_format]}}}{suffix}",
            )
        )
    if reference is not None:
        fig.add_hline(y=reference, line_color=BASELINE, line_width=1)
    fig.update_layout(showlegend=len(df.columns) > 1)
    fig = _layout(fig, y_format, height, log, y_title)
    fig.update_xaxes(hoverformat="%b %d, %Y" if langue() == "en" else "%d/%m/%Y")
    if log:
        # Graduations par paliers ×2 : chaque palier = un doublement de la valeur.
        lo, hi = df.min().min(), df.max().max()
        ticks = [12.5 * 2 ** k for k in range(12)]
        tickvals = [t for t in ticks if lo / 1.5 <= t <= hi * 1.5]
        # Texte des graduations écrit à la main : sur un axe log, Plotly n'ajoute l'unité
        # qu'aux puissances de 10.
        numbers = [f"{t:,.1f}".rstrip("0").rstrip(".") for t in tickvals]
        if langue() != "en":
            numbers = [n.replace(",", " ").replace(".", ",") for n in numbers]
        ticktext = [f"{prefix}{n}{suffix}" for n in numbers]
        fig.update_yaxes(tickvals=tickvals, ticktext=ticktext, minor=dict(showgrid=False))
    return fig


def bars(
    df: pd.DataFrame,
    y_format: str = "pct",
    colors: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    height: int = 380,
) -> go.Figure:
    """Barres groupées : une série par colonne, une catégorie par ligne."""
    colors = colors or COLORS
    labels = labels or asset_labels()
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(
            go.Bar(
                x=[str(i) for i in df.index], y=df[col], name=labels.get(col, col),
                marker=dict(color=colors.get(col, INK_SECONDARY), line=dict(width=0)),
                hovertemplate=f"%{{y:{FORMATS[y_format]}}}",
            )
        )
    fig.add_hline(y=0, line_color=BASELINE, line_width=1)
    single = len(df.columns) == 1
    # Barres fines : une seule série laisse plus d'air entre les catégories.
    fig.update_layout(barmode="group", bargap=0.6 if single else 0.35, bargroupgap=0.08, showlegend=not single)
    fig = _layout(fig, y_format, height)
    fig.update_layout(hovermode="x unified")
    return fig


def stacked_shares(shares: pd.DataFrame, colors: Optional[Dict[str, str]] = None, height: int = 220) -> go.Figure:
    """Barres horizontales empilées à 100 % (lignes = barres, colonnes = segments)."""
    colors = colors or COLORS
    fig = go.Figure()
    for col in shares.columns:
        fig.add_trace(
            go.Bar(
                y=list(shares.index), x=shares[col], orientation="h", name=asset_labels().get(col, col),
                marker=dict(color=colors.get(col, INK_SECONDARY), line=dict(color=SURFACE, width=2)),
                text=[pct(v, 0) if v >= 0.06 else "" for v in shares[col]], textposition="inside",
                insidetextanchor="middle", hovertemplate="%{x:.1%}",
            )
        )
    fig = _layout(fig, "pct", height)
    fig.update_layout(barmode="stack", bargap=0.45, hovermode="y unified", legend=dict(traceorder="normal"))
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, 1])
    fig.update_yaxes(type="category", autorange="reversed", gridcolor=SURFACE, tickformat="",
                     tickfont=dict(color=INK_SECONDARY))
    return fig


def _wash(hex_color: str, alpha: float = 0.10) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def ranking(values: pd.Series, value_label: str, height: int = 360) -> go.Figure:
    """Classement en barres horizontales, la plus grande valeur en haut, valeurs écrites au bout."""
    fig = go.Figure(
        go.Bar(
            y=list(values.index), x=values.values, orientation="h",
            marker=dict(color=INK_SECONDARY, line=dict(width=0)),
            text=[str(v) for v in values.values], textposition="outside", cliponaxis=False,
            textfont=dict(color=INK_SECONDARY),
            hovertemplate=f"%{{x}} {value_label}<extra></extra>",
        )
    )
    fig = _layout(fig, "num", height)
    fig.update_layout(bargap=0.45, hovermode="closest", showlegend=False)
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, values.max() * 1.12])
    fig.update_yaxes(type="category", autorange="reversed", gridcolor=SURFACE, tickformat="",
                     tickfont=dict(color=INK_SECONDARY))
    return fig
