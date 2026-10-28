"""Dashboard : la cryptomonnaie est-elle devenue un actif comme les autres ?

Lancement en local :
    streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR.parent))
sys.path.insert(0, str(APP_DIR))

import pandas as pd
import streamlit as st

import plots
from langue import big_dollars, date, dollars, langue, num, pct, rang, selecteur_langue, tr
from src.analysis import data
from src.analysis import metrics as m
from src.analysis import portfolio as pf

st.set_page_config(page_title=tr("Cryptomonnaie vs Bourse", "Crypto vs Stock Market"), page_icon="📈", layout="wide")

CRYPTOS = ["BTC", "ETH", "SOL"]
MARKETS = ["NDX", "SPX", "CAC", "GOLD", "TLT"]
ANALYSED = CRYPTOS + MARKETS
WINDOWS = {21: ("1 mois", "1 month"), 63: ("3 mois", "3 months"), 126: ("6 mois", "6 months"), 252: ("1 an", "1 year")}
CRISIS_NAMES = {
    "2018-01": ("Fév. 2018", "Feb 2018"),
    "2018-09": ("Fin 2018", "Late 2018"),
    "2020-02": ("COVID", "COVID"),
    "2022-01": ("Inflation 2022", "2022 inflation"),
    "2025-02": ("Droits de douane", "Tariffs"),
}
REBALANCE_NAMES = {
    "mensuel": ("Mensuel", "Monthly"), "trimestriel": ("Trimestriel", "Quarterly"),
    "annuel": ("Annuel", "Yearly"), "jamais": ("Jamais", "Never"),
}
CHART = {"config": {"displayModeBar": False}, "use_container_width": True}


def name(symbol: str) -> str:
    return plots.asset_labels().get(symbol, symbol)


# --- Données --------------------------------------------------------------------

@st.cache_data(ttl=6 * 3600, show_spinner="Chargement des données… / Loading data…")
def load():
    return {
        "assets": data.load_assets(),
        "log": data.load_aligned("log_return"),
        "simple": data.load_aligned("simple_return"),
        "prices": data.load_aligned("price"),
        "native": data.load_native("log_return"),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_trending() -> pd.DataFrame:
    try:
        df = data.load_table("fct_trending")
    except Exception:  # table absente d'un ancien export : la section l'indique
        return pd.DataFrame()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


@st.cache_data(show_spinner=False)
def crises(threshold: float, lang: str) -> pd.DataFrame:
    episodes = m.drawdown_episodes(D["prices"]["SPX"].dropna(), threshold=-threshold)
    names = {k: v[1] if lang == "en" else v[0] for k, v in CRISIS_NAMES.items()}
    episodes["nom"] = episodes["sommet"].dt.strftime("%Y-%m").map(names)
    episodes["nom"] = episodes["nom"].fillna(episodes["sommet"].dt.strftime("%m/%Y"))
    return episodes


D = load()
start, end = D["log"].index.min(), D["log"].index.max()

_, language_column = st.columns([5, 1])
selecteur_langue(language_column)

st.title(tr("La cryptomonnaie est-elle devenue un actif comme les autres ?",
            "Has cryptocurrency become an asset like any other?"))
st.caption(tr(
    f"Bitcoin, Ethereum et Solana face aux actions, obligations et or · "
    f"données du {date(start)} au {date(end)}, mises à jour chaque jour",
    f"Bitcoin, Ethereum and Solana versus stocks, bonds and gold · "
    f"data from {date(start)} to {date(end)}, updated daily",
))

# Un sélecteur plutôt que des onglets : il garde la section ouverte quand un réglage
# relance la page, et seule la section affichée est calculée. Les options sont des clés
# fixes : changer de langue ne referme pas la section ouverte.
SECTIONS = {
    "overview": ("Vue d'ensemble", "Overview"),
    "link": ("Lien avec la bourse", "Link to the stock market"),
    "risk": ("Risque et krachs", "Risk and crashes"),
    "simulator": ("Simulateur de portefeuille", "Portfolio simulator"),
    "trending": ("Cryptomonnaies tendance", "Trending cryptocurrencies"),
}
# Streamlit recrée un sélecteur dont les libellés changent : la section ouverte est donc
# mémorisée à part, pour rester la même quand on change de langue.
section = st.segmented_control(
    "Section", list(SECTIONS), default=st.session_state.get("open_section", "overview"),
    format_func=lambda k: tr(*SECTIONS[k]), key=f"section_{langue()}", label_visibility="collapsed",
) or "overview"
st.session_state["open_section"] = section


# --- Vue d'ensemble -------------------------------------------------------------

if section == "overview":
    st.markdown(tr(
        "**En bref : la cryptomonnaie est devenue un actif lié aux marchés, mais pas un actif comme les autres.** "
        "Depuis 2020, elle bouge en partie avec la bourse américaine (corrélation autour de 0,4, contre 0 avant) ; "
        "elle reste bien plus volatile ; elle ne protège pas pendant les krachs, et a en plus ses propres krachs.",
        "**In short: cryptocurrency has become an asset tied to the markets, but not an asset like any other.** "
        "Since 2020, it has partly moved with the US stock market (correlation around 0.4, versus 0 before); "
        "it remains far more volatile; it offers no protection during crashes, and has its own crashes on top.",
    ))

    corr = m.rolling_correlation(D["log"], "BTC", "NDX", 63).dropna()
    vol_btc = m.rolling_volatility(D["log"], "BTC", 252).dropna()
    vol_ndx = m.rolling_volatility(D["log"], "NDX", 252).dropna()
    ratio = (vol_btc / vol_ndx).dropna()
    btc = D["prices"]["BTC"].dropna()
    drawdown_btc = m.drawdown(btc)

    year_ago = end - pd.DateOffset(years=1)
    def a_year_ago(series: pd.Series) -> float:
        return series.loc[:year_ago].iloc[-1]

    over_a_year = tr("sur un an", "over a year")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        tr("Corrélation BTC / Nasdaq", "BTC / Nasdaq correlation"), num(corr.iloc[-1]),
        f"{num(corr.iloc[-1] - a_year_ago(corr), sign=True)} {over_a_year}", delta_color="off",
        help=tr("Sur les 3 derniers mois de bourse. 0 = aucun lien, 1 = mouvements identiques.",
                "Over the last 3 months of trading. 0 = no link, 1 = identical moves."),
    )
    c2.metric(
        tr("Volatilité du Bitcoin", "Bitcoin volatility"), pct(vol_btc.iloc[-1], 0),
        f"{num((vol_btc.iloc[-1] - a_year_ago(vol_btc)) * 100, 1, sign=True)} pt {over_a_year}", delta_color="off",
        help=tr("Écart-type annualisé des rendements journaliers sur la dernière année de bourse.",
                "Annualized standard deviation of daily returns over the last year of trading."),
    )
    c3.metric(
        tr("Volatilité BTC / Nasdaq", "BTC / Nasdaq volatility"), f"× {num(ratio.iloc[-1], 1)}",
        f"{num(ratio.iloc[-1] - a_year_ago(ratio), 1, sign=True)} {over_a_year}", delta_color="off",
        help=tr("Combien de fois le Bitcoin est plus volatil que le Nasdaq, sur un an glissant.",
                "How many times more volatile Bitcoin is than the Nasdaq, over a rolling year."),
    )
    c4.metric(
        tr("Bitcoin vs son record", "Bitcoin vs its record"), pct(drawdown_btc.iloc[-1], 0),
        help=tr(f"Baisse par rapport au plus haut historique, atteint le {date(btc.idxmax())}.",
                f"Decline from the all-time high, reached on {date(btc.idxmax())}."),
    )

    st.subheader(tr("Ce que sont devenus 100 $ investis", "What $100 invested has become"))
    col_a, col_b = st.columns([4, 1])
    chosen = col_a.multiselect(
        tr("Actifs", "Assets"), ANALYSED, default=["BTC", "SPX", "GOLD", "TLT"], format_func=name, key="growth_assets"
    )
    log_scale = col_b.toggle(tr("Échelle logarithmique", "Logarithmic scale"), value=True, key="log_scale")
    if chosen:
        prices = D["prices"][chosen].dropna()
        st.caption(tr(f"Base 100 au {date(prices.index[0])}, premier jour commun aux actifs choisis.",
                      f"Base 100 on {date(prices.index[0])}, the first day shared by the selected assets."))
        st.plotly_chart(plots.lines(
            prices / prices.iloc[0] * 100, "money", log=log_scale,
            y_title=tr("Valeur du placement (en dollars)", "Value of the investment (in dollars)"),
        ), **CHART)


# --- Lien avec la bourse ----------------------------------------------------------

if section == "link":
    c1, c2, c3 = st.columns(3)
    crypto = c1.selectbox(tr("Cryptomonnaie", "Cryptocurrency"), CRYPTOS, format_func=name, key="link_crypto")
    market = c2.selectbox(tr("Comparée à", "Compared with"), MARKETS, format_func=name, key="link_market")
    window = c3.radio(tr("Fenêtre", "Window"), list(WINDOWS), index=1, horizontal=True,
                      format_func=lambda w: tr(*WINDOWS[w]), key="link_window")
    window_label = tr(*WINDOWS[window])

    rolling = m.rolling_correlation(D["log"], crypto, market, window).dropna()
    bands = crises(0.10, langue())
    bands = bands[bands["point_bas"] >= rolling.index[0]]
    st.subheader(tr(f"Corrélation {name(crypto)} / {name(market)} sur {window_label} glissants",
                    f"{name(crypto)} / {name(market)} correlation over a rolling {window_label}"))
    st.caption(tr("Bandes grises : baisses de plus de 10 % du S&P 500, du sommet au point bas.",
                  "Grey bands: S&P 500 declines of more than 10%, from peak to trough."))
    st.plotly_chart(
        plots.lines(rolling.to_frame(market), "num", bands=bands, reference=0, height=400), **CHART
    )

    left, right = st.columns([3, 2])
    with left:
        st.subheader(tr("Année par année", "Year by year"))
        yearly = m.yearly_correlation(D["log"], crypto, market).to_frame(market)
        st.plotly_chart(plots.bars(yearly, "num", height=320), **CHART)
    with right:
        st.subheader(tr("Selon le sens du marché", "Depending on market direction"))
        cond = m.conditional_correlation(D["log"], crypto, market)
        down, everyday, up = cond.values
        st.metric(tr(f"Jours de baisse de plus de 1 % ({name(market)})",
                     f"Days down more than 1% ({name(market)})"), num(down))
        st.metric(tr("Tous les jours", "All days"), num(everyday))
        st.metric(tr(f"Jours de hausse de plus de 1 % ({name(market)})",
                     f"Days up more than 1% ({name(market)})"), num(up))
        if down > up + 0.05:
            st.caption(tr(
                f"{name(crypto)} suit davantage {name(market)} quand il chute que quand il monte : "
                "c'est le contraire d'une protection.",
                f"{name(crypto)} follows the {name(market)} more when it falls than when it rises: "
                "the opposite of a hedge.",
            ))


# --- Risque et krachs -----------------------------------------------------------

if section == "risk":
    chosen = st.multiselect(
        tr("Actifs", "Assets"), ANALYSED, default=["BTC", "NDX", "GOLD"], format_func=name, key="risk_assets"
    )
    if chosen:
        left, right = st.columns(2)
        with left:
            st.subheader(tr("Volatilité sur 1 an glissant", "Volatility over a rolling year"))
            vols = pd.DataFrame({s: m.rolling_volatility(D["log"], s, 252) for s in chosen}).dropna(how="all")
            st.plotly_chart(plots.lines(vols, "pct", height=360), **CHART)
        with right:
            st.subheader(tr("Baisse depuis le plus haut historique", "Decline from the all-time high"))
            dd = pd.DataFrame({s: m.drawdown(D["prices"][s].dropna()) for s in chosen})
            st.plotly_chart(plots.lines(dd, "pct", fill=True, height=360), **CHART)

    st.subheader(tr("Performance et risque depuis 2018", "Performance and risk since 2018"))
    summary = m.summary_table(D["native"][ANALYSED], D["assets"]).sort_values("volatilite_annuelle", ascending=False)
    summary.index = summary.index.map(name).rename(tr("Actif", "Asset"))
    st.dataframe(
        summary.drop(columns="classe").style.format(
            {"rendement_annuel": lambda v: pct(v, 1, sign=True), "volatilite_annuelle": lambda v: pct(v, 0),
             "sharpe": num, "pire_baisse": lambda v: pct(v, 0), "pire_jour": lambda v: pct(v, 0)}
        ),
        column_config={
            "depuis": tr("Depuis", "Since"),
            "rendement_annuel": tr("Rendement annuel", "Annual return"),
            "volatilite_annuelle": tr("Volatilité", "Volatility"),
            "sharpe": st.column_config.Column(
                "Sharpe", help=tr("Rendement par unité de risque (taux sans risque à 0)",
                                  "Return per unit of risk (risk-free rate set to 0)")
            ),
            "pire_baisse": tr("Pire baisse", "Worst decline"),
            "pire_jour": tr("Pire jour", "Worst day"),
        },
        use_container_width=True,
    )

    st.subheader(tr("Pendant les krachs boursiers", "During stock market crashes"))
    threshold = st.slider(
        tr("Seuil de krach (baisse du S&P 500 depuis un sommet)", "Crash threshold (S&P 500 decline from a peak)"),
        5, 30, 10, step=1, format="%d %%" if langue() == "fr" else "%d%%", key="crash_threshold",
    ) / 100
    episodes = crises(threshold, langue())
    if episodes.empty:
        st.info(tr("Aucun krach de cette ampleur sur la période.", "No crash of this size over the period."))
    else:
        perf = pd.DataFrame(
            {
                e["nom"]: m.performance_during(D["prices"][["SPX", "BTC", "TLT", "GOLD"]], e["sommet"], e["point_bas"])
                for _, e in episodes.iterrows()
            }
        ).T
        st.caption(tr(
            f"Variation de chaque actif entre le sommet et le point bas du S&P 500 ({len(episodes)} épisodes).",
            f"Change in each asset between the S&P 500 peak and trough ({len(episodes)} episodes).",
        ))
        st.plotly_chart(plots.bars(perf, "pct", height=360), **CHART)


# --- Simulateur ---------------------------------------------------------------------

if section == "simulator":
    st.markdown(tr(
        "Un portefeuille actions / obligations, dans lequel on remplace une part par de la cryptomonnaie "
        "(ou de l'or, pour comparer). ETF réellement achetables, dividendes réinvestis ; "
        "le ratio de Sharpe mesure le rendement **au-dessus du cash**.",
        "A stock / bond portfolio in which part of the holdings is replaced with cryptocurrency "
        "(or gold, for comparison). ETFs you can actually buy, dividends reinvested; "
        "the Sharpe ratio measures return **above cash**.",
    ))
    choices = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "GLD": tr("Or (ETF)", "Gold (ETF)")}
    percent = "%d %%" if langue() == "fr" else "%d%%"
    c1, c2, c3 = st.columns(3)
    stocks = c1.slider(tr("Part d'actions (le reste en obligations)", "Share of stocks (the rest in bonds)"),
                       0, 100, 60, step=5, format=percent, key="sim_stocks") / 100
    extra = c2.selectbox(tr("Actif ajouté", "Added asset"), list(choices), format_func=choices.get, key="sim_extra")
    share = c3.slider(tr("Part de l'actif ajouté", "Share of the added asset"),
                      0, 30, 5, step=1, format=percent, key="sim_share") / 100
    c4, c5, c6 = st.columns(3)
    rebalance_key = c4.selectbox(tr("Rééquilibrage", "Rebalancing"), list(pf.REBALANCE), index=0,
                                 format_func=lambda k: tr(*REBALANCE_NAMES[k]), key="sim_rebalance")
    first_year = c5.selectbox(tr("Début de la simulation", "Simulation start"),
                              list(range(start.year, end.year - 1)), index=0, key="sim_start")
    cost = c6.select_slider(tr("Frais par achat / vente", "Fees per buy / sell"), [0.0, 0.001, 0.0025, 0.005],
                            value=0.001, format_func=lambda v: pct(v, 2), key="sim_cost")

    base = {k: v for k, v in {"SPY": stocks, "TLT": 1 - stocks}.items() if v > 0}
    with_extra = pf.mix(base, {extra: share})
    window = D["simple"].loc[str(first_year):, list(set(base) | {extra, "BIL"})].dropna()
    rebalance = pf.REBALANCE[rebalance_key]

    runs = {
        tr("Sans ajout", "Without addition"): pf.backtest(window, base, rebalance, cost),
        tr(f"Avec {pct(share, 0)} de {choices[extra]}", f"With {pct(share, 0)} {choices[extra]}"):
            pf.backtest(window, with_extra, rebalance, cost),
    }
    ref_name, new_name = list(runs)
    results = {k: pf.evaluate(v["valeur"], window["BIL"]) for k, v in runs.items()}
    new, ref = results[new_name], results[ref_name]

    st.caption(tr(f"Simulation du {date(window.index[0])} au {date(window.index[-1])}.",
                  f"Simulation from {date(window.index[0])} to {date(window.index[-1])}."))
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(tr("Rendement annuel", "Annual return"), pct(new["rendement_annuel"]),
              f"{num((new['rendement_annuel'] - ref['rendement_annuel']) * 100, 1, sign=True)} pt", delta_color="normal")
    k2.metric(tr("Volatilité", "Volatility"), pct(new["volatilite"]),
              f"{num((new['volatilite'] - ref['volatilite']) * 100, 1, sign=True)} pt", delta_color="inverse")
    k3.metric(tr("Ratio de Sharpe", "Sharpe ratio"), num(new["sharpe"]), num(new["sharpe"] - ref["sharpe"], sign=True),
              delta_color="normal")
    k4.metric(tr("Pire baisse", "Worst decline"), pct(new["pire_baisse"]),
              f"{num((new['pire_baisse'] - ref['pire_baisse']) * 100, 1, sign=True)} pt", delta_color="normal")
    st.caption(tr("Écarts par rapport au même portefeuille sans ajout.",
                  "Differences versus the same portfolio without the addition."))

    sim_colors = {ref_name: plots.REFERENCE, new_name: plots.COLORS[extra]}
    sim_labels = {k: k for k in runs}
    left, right = st.columns(2)
    with left:
        st.subheader(tr("Valeur de 100 $ investis", "Value of $100 invested"))
        growth = pd.DataFrame({k: v["valeur"] / v["valeur"].iloc[0] * 100 for k, v in runs.items()})
        st.plotly_chart(plots.lines(growth, "money", colors=sim_colors, labels=sim_labels, height=360), **CHART)
    with right:
        st.subheader(tr("Baisse depuis le plus haut", "Decline from the peak"))
        dd = pd.DataFrame({k: m.drawdown(v["valeur"]) for k, v in runs.items()})
        st.plotly_chart(plots.lines(dd, "pct", colors=sim_colors, labels=sim_labels, height=360), **CHART)

    if share > 0:
        risk = pf.risk_contribution(window, with_extra)
        shares = pd.DataFrame(
            [pd.Series(with_extra), risk],
            index=[tr("Part du capital", "Share of capital"), tr("Part du risque", "Share of risk")],
        )
        st.subheader(tr(f"{pct(share, 0)} du capital, {pct(risk[extra], 0)} du risque",
                        f"{pct(share, 0)} of capital, {pct(risk[extra], 0)} of risk"))
        st.plotly_chart(plots.stacked_shares(shares), **CHART)

    st.caption(tr(
        "Simulation sur données passées : elle ne dit rien des rendements futurs. "
        "Les cryptomonnaies étudiées ont survécu et fortement monté (biais du survivant). "
        "Ce n'est pas un conseil d'investissement.",
        "Simulation on past data: it says nothing about future returns. "
        "The cryptocurrencies studied survived and rose sharply (survivorship bias). "
        "This is not investment advice.",
    ))


# --- Cryptomonnaies tendance ------------------------------------------------------

if section == "trending":
    trending = load_trending()
    if trending.empty:
        st.info(tr("Aucun classement disponible pour l'instant : il sera ajouté à la prochaine mise à jour des données.",
                   "No ranking available yet: it will be added at the next data update."))
        st.stop()

    snapshots = sorted(trending["snapshot_date"].unique())
    latest = pd.Timestamp(snapshots[-1])
    today = trending[trending["snapshot_date"] == latest].sort_values("position")

    st.subheader(tr(f"Les {len(today)} cryptomonnaies les plus recherchées le {date(latest)}",
                    f"The {len(today)} most searched cryptocurrencies on {date(latest)}"))
    st.caption(tr(
        "Classement CoinGecko des cryptomonnaies les plus recherchées par ses utilisateurs sur 24 heures, "
        "relevé chaque matin. Être en tendance mesure la curiosité du public, pas la qualité d'un actif.",
        "CoinGecko ranking of the cryptocurrencies most searched by its users over 24 hours, "
        "recorded every morning. Trending measures public curiosity, not the quality of an asset.",
    ))

    rising = int((today["change_24h"] > 0).sum())
    small = int((today["market_cap_rank"].isna() | (today["market_cap_rank"] > 100)).sum())
    newcomers = int((today["days_trending"] == 1).sum())
    first = today.iloc[0]
    out_of = tr("sur", "of")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("La plus recherchée", "Most searched"), f"{first['name']} ({first['symbol']})")
    c2.metric(tr("En hausse sur 24 h", "Up over 24h"), f"{rising} {out_of} {len(today)}")
    c3.metric(
        tr("Hors du top 100", "Outside the top 100"), f"{small} {out_of} {len(today)}",
        help=tr("Cryptomonnaies classées au-delà de la 100e place par capitalisation, ou non classées.",
                "Cryptocurrencies ranked beyond 100th by market cap, or unranked."),
    )
    if len(snapshots) > 1:
        c4.metric(
            tr("Nouvelles venues", "Newcomers"), newcomers,
            help=tr(f"En tendance pour la première fois depuis le début de l'historique, le {date(snapshots[0])}.",
                    f"Trending for the first time since the history began on {date(snapshots[0])}."),
        )
    else:
        c4.metric(tr("Jours d'historique", "Days of history"), 1,
                  help=tr("L'historique s'enrichit d'une photo du classement chaque jour.",
                          "The history grows by one snapshot of the ranking every day."))

    col_rank = tr("Rang capitalisation", "Market cap rank")
    col_streak = tr("Jours d'affilée", "Days in a row")
    table = pd.DataFrame(
        {
            "": today["image_url"],
            "#": today["position"],
            tr("Cryptomonnaie", "Cryptocurrency"): today["name"],
            tr("Symbole", "Symbol"): today["symbol"],
            col_rank: today["market_cap_rank"].map(rang),
            tr("Prix", "Price"): today["price_usd"].map(dollars),
            tr("Variation 24 h", "24h change"): today["change_24h"].map(lambda v: pct(v, 1, sign=True)),
            tr("Capitalisation", "Market cap"): today["market_cap_usd"].map(big_dollars),
            tr("Volume 24 h", "24h volume"): today["volume_24h_usd"].map(big_dollars),
            col_streak: today["streak_days"],
        }
    )
    st.dataframe(
        table, hide_index=True, use_container_width=True, height=(len(table) + 1) * 35 + 3,
        column_config={
            "": st.column_config.ImageColumn(width=40),
            "#": st.column_config.NumberColumn(width=40),
            col_rank: st.column_config.TextColumn(tr("Rang capi.", "Cap rank")),
            col_streak: st.column_config.NumberColumn(
                help=tr("Jours de collecte consécutifs où la cryptomonnaie figure dans le classement.",
                        "Consecutive collection days on which the cryptocurrency appears in the ranking.")
            ),
        },
    )

    st.subheader(tr("Les habituées du classement", "Ranking regulars"))
    if len(snapshots) < 2:
        st.info(tr(
            f"L'historique a démarré le {date(latest)}. Dès demain, cette partie montrera les cryptomonnaies "
            "qui reviennent le plus souvent en tendance.",
            f"The history started on {date(latest)}. From tomorrow, this part will show the cryptocurrencies "
            "that trend most often.",
        ))
    else:
        recent = trending[trending["snapshot_date"].isin(snapshots[-30:])]
        n_days = recent["snapshot_date"].nunique()
        counts = (
            recent.assign(label=recent["name"] + " (" + recent["symbol"] + ")")
            .groupby("label")
            .size()
            .sort_index()
            .sort_values(ascending=False, kind="stable")  # à égalité : ordre alphabétique
            .head(10)
        )
        st.caption(tr(f"Nombre de jours en tendance sur les {n_days} derniers jours de collecte, 10 premières.",
                      f"Number of days trending over the last {n_days} collection days, top 10."))
        st.plotly_chart(plots.ranking(counts, tr("jours", "days"), height=40 * len(counts) + 60), **CHART)

    st.caption(tr("Source : API publique CoinGecko. Ce n'est pas un conseil d'investissement.",
                  "Source: CoinGecko public API. This is not investment advice."))
