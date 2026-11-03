"""Outils de l'assistant : chaque outil est une fonction Python qui renvoie un dictionnaire
sérialisable en JSON, décrit par un schéma JSON que le modèle lit pour savoir l'appeler.

Rien ici ne dépend du fournisseur du modèle : les mêmes outils et les mêmes schémas
peuvent servir à Gemini, à Claude ou à un autre modèle.

Les chiffres donnés à l'utilisateur viennent toujours de ces outils : le modèle choisit
quoi calculer et rédige la réponse, il ne calcule rien lui-même.
"""
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import duckdb
import numpy as np
import pandas as pd

from src.analysis import metrics as m
from src.analysis import portfolio as pf

TABLES = ["dim_assets", "fct_daily_returns", "fct_aligned_returns", "fct_trending"]
MAX_ROWS = 200          # lignes renvoyées au modèle par requête
SQL_TIMEOUT = 10        # secondes avant d'interrompre une requête trop longue
ADDABLE = ["BTC", "ETH", "SOL", "GLD"]

# Description des tables donnée au modèle, pour qu'il écrive des requêtes justes.
SCHEMA = """\
Tables disponibles (DuckDB, SQL standard) :

dim_assets : un actif par ligne
  symbol, name, asset_class (crypto | action | obligation | matiere_premiere | monetaire),
  source, periods_per_year (365 pour la crypto, 252 sinon), first_date, last_date, nb_quotes

fct_daily_returns : rendements de chaque actif sur SON PROPRE calendrier (crypto 7j/7, bourse 5j/7).
  À utiliser pour étudier un actif seul (volatilité, rendement, pire baisse).
  symbol, date, price, simple_return, log_return, days_since_prev

fct_aligned_returns : rendements de tous les actifs sur le calendrier de la bourse US (jours ouvrés).
  À utiliser pour COMPARER des actifs (corrélations, portefeuilles). Le rendement crypto
  du lundi couvre vendredi -> lundi.
  symbol, date, price, quote_date, is_carried_forward, staleness_days, simple_return, log_return

fct_trending : cryptomonnaies les plus recherchées sur CoinGecko, une photo par jour.
  snapshot_date, position (1 = la plus recherchée), coin_id, symbol, name, market_cap_rank,
  price_usd, change_24h (fraction : 0.05 = +5 %), market_cap_usd, volume_24h_usd, image_url,
  days_trending (jours en tendance jusqu'à cette date), streak_days (jours consécutifs), first_seen

Actifs (colonne symbol) :
  BTC Bitcoin, ETH Ethereum, SOL Solana (crypto) ;
  SPX S&P 500, NDX Nasdaq Composite, CAC CAC 40 (indices boursiers, sans dividendes) ;
  SPY ETF S&P 500 (dividendes réinvestis), TLT ETF obligations US 20 ans+, BIL ETF bons du
  Trésor US 1-3 mois (placement sans risque), GOLD or (contrat future), GLD ETF or.

Conventions :
  - simple_return et change_24h sont des fractions (0.05 = +5 %).
  - Volatilité annuelle = stddev(log_return) * sqrt(periods_per_year), sur fct_daily_returns.
  - Corrélation = corr(a.log_return, b.log_return) en joignant fct_aligned_returns sur la date.
  - Performance sur une période = exp(sum(log_return)) - 1 sur fct_daily_returns : pour une année,
    elle part de la clôture de l'année précédente (convention habituelle).
  - Une requête qui ne renvoie rien vient souvent d'un filtre trop strict : vérifier le symbole et
    les dates avant de conclure que la donnée n'existe pas.
"""

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "interroger_donnees",
        "description": (
            "Exécute une requête SQL en lecture seule (un seul SELECT ou WITH) sur les tables du projet "
            "et renvoie au plus 200 lignes. À utiliser pour tout chiffre : prix, rendements, volatilité, "
            "corrélations, tendances.\n\n" + SCHEMA
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "La requête SQL (DuckDB), un seul SELECT ou WITH."},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "simuler_portefeuille",
        "description": (
            "Simule sur données passées un portefeuille actions (ETF SPY) / obligations (ETF TLT) dans "
            "lequel on remplace une part par un actif ajouté, et le compare au même portefeuille sans ajout. "
            "Frais payés à chaque rééquilibrage, ratio de Sharpe calculé au-dessus du cash (ETF BIL). "
            "Renvoie le rendement annuel, la volatilité, le ratio de Sharpe, la pire baisse, et la part "
            "du risque apportée par l'actif ajouté."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "actif_ajoute": {"type": "string", "enum": ADDABLE,
                                 "description": "BTC, ETH, SOL, ou GLD (or) pour comparer."},
                "part_ajoutee": {"type": "number", "description": "Part de l'actif ajouté, de 0 à 0.3 (0.05 = 5 %)."},
                "part_actions": {"type": "number",
                                 "description": "Part d'actions avant l'ajout, de 0 à 1 (0.6 = portefeuille 60/40). "
                                                "Par défaut 0.6."},
                "reequilibrage": {"type": "string", "enum": list(pf.REBALANCE),
                                  "description": "Fréquence du retour aux poids cibles. Par défaut mensuel."},
                "annee_debut": {"type": "integer", "description": "Année de départ de la simulation (2018 à 2024). "
                                                                  "Par défaut, le début des données."},
                "frais": {"type": "number", "description": "Frais par achat ou vente (0.001 = 0,1 %). Par défaut 0.001."},
            },
            "required": ["actif_ajoute", "part_ajoutee"],
        },
    },
    {
        "name": "lister_krachs",
        "description": (
            "Liste les krachs du S&P 500 détectés automatiquement (baisse d'au moins `seuil` depuis un sommet), "
            "avec pour chacun les dates, la baisse du S&P 500, et la variation de chaque actif entre le "
            "sommet et le point bas. À utiliser en priorité pour toute question sur un krach ou une crise "
            "(COVID en 2020, inflation en 2022...) : ce sont les mêmes chiffres que dans le dashboard."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "seuil": {"type": "number", "description": "Baisse minimale, de 0.05 à 0.5 (0.1 = 10 %). Par défaut 0.1."},
            },
        },
    },
    {
        "name": "tracer_graphique",
        "description": (
            "Affiche un graphique à l'utilisateur à partir d'une requête SQL (mêmes tables que interroger_donnees). "
            "Deux formes de résultat acceptées : (1) large : la 1re colonne est l'axe horizontal (date ou "
            "catégorie), chaque autre colonne est une série ; (2) longue : exactement 3 colonnes "
            "(axe, nom de la série, valeur). Utiliser des symboles d'actifs (BTC, SPX...) comme noms de séries "
            "pour avoir les bonnes couleurs. Au plus 2000 points par série. Ne tracer que si un graphique aide "
            "vraiment à comprendre la réponse."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "La requête SQL qui produit les données du graphique."},
                "type": {"type": "string", "enum": ["ligne", "barres"],
                         "description": "ligne pour une évolution dans le temps, barres pour comparer des catégories."},
                "titre": {"type": "string", "description": "Titre court du graphique, dans la langue de l'utilisateur."},
                "unite": {"type": "string", "enum": ["pct", "money", "num"],
                          "description": "pct si les valeurs sont des fractions (0.05 = 5 %), money pour des dollars, "
                                         "num sinon."},
            },
            "required": ["sql", "type", "titre", "unite"],
        },
    },
]


@dataclass
class Graphique:
    """Graphique demandé par le modèle, affiché ensuite par le dashboard."""
    type: str
    titre: str
    unite: str
    donnees: pd.DataFrame


class ErreurOutil(Exception):
    """Erreur renvoyée au modèle (requête invalide, paramètre hors limites) pour qu'il corrige."""


def _json_value(v: Any) -> Any:
    """Valeur lisible et compacte pour le modèle : dates en texte, nombres arrondis."""
    if v is None or (pd.api.types.is_scalar(v) and pd.isna(v)):   # None, NaN et dates vides (NaT)
        return None
    if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "isoformat"):
        ts = pd.Timestamp(v)
        return ts.date().isoformat() if ts == ts.normalize() else ts.isoformat()
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(f"{float(v):.6g}")
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _records(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "colonnes": list(df.columns),
        "lignes": [[_json_value(v) for v in row] for row in df.itertuples(index=False)],
    }


@dataclass
class Boite:
    """Les outils, liés aux données du moment. Une boîte par question : elle garde les
    graphiques demandés et les étapes suivies, que le dashboard affiche ensuite."""

    tables: Dict[str, pd.DataFrame]
    graphiques: List[Graphique] = field(default_factory=list)
    _con: Optional[duckdb.DuckDBPyConnection] = None

    # --- SQL : une base en mémoire, isolée, qui ne contient que des copies des tables ---

    def _connexion(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            con = duckdb.connect(":memory:")
            for name in TABLES:
                if name in self.tables:
                    con.register("_source", self.tables[name])
                    con.execute(f"create table {name} as select * from _source")
                    con.unregister("_source")
            # Plus aucun accès aux fichiers, au réseau ni aux extensions, et réglages verrouillés :
            # une requête ne peut lire que les tables copiées ci-dessus.
            con.execute("set enable_external_access = false")
            con.execute("set threads = 1")
            con.execute("set memory_limit = '500MB'")
            con.execute("set lock_configuration = true")
            self._con = con
        return self._con

    def _sql(self, sql: str, max_rows: int) -> pd.DataFrame:
        query = sql.strip().rstrip(";").strip()
        if ";" in query:
            raise ErreurOutil("Une seule requête à la fois.")
        if not re.match(r"(?is)^\s*(select|with)\b", query):
            raise ErreurOutil("Seules les requêtes SELECT (ou WITH ... SELECT) sont autorisées.")
        con = self._connexion()
        timer = threading.Timer(SQL_TIMEOUT, con.interrupt)
        timer.start()
        try:
            return con.execute(f"select * from ({query}) limit {max_rows + 1}").df()
        except duckdb.InterruptException:
            raise ErreurOutil(f"Requête trop longue (plus de {SQL_TIMEOUT} s) : la simplifier.")
        except duckdb.Error as e:
            raise ErreurOutil(f"Erreur SQL : {e}")
        finally:
            timer.cancel()

    def interroger_donnees(self, sql: str) -> Dict[str, Any]:
        df = self._sql(sql, MAX_ROWS)
        out = _records(df.head(MAX_ROWS))
        out["tronque"] = len(df) > MAX_ROWS
        return out

    # --- Simulation de portefeuille ---

    def _wide(self, value: str) -> pd.DataFrame:
        df = self.tables["fct_aligned_returns"]
        wide = df.pivot(index="date", columns="symbol", values=value)
        wide.index = pd.to_datetime(wide.index)
        return wide.sort_index()

    def simuler_portefeuille(
        self,
        actif_ajoute: str,
        part_ajoutee: float,
        part_actions: float = 0.6,
        reequilibrage: str = "mensuel",
        annee_debut: Optional[int] = None,
        frais: float = 0.001,
    ) -> Dict[str, Any]:
        if actif_ajoute not in ADDABLE:
            raise ErreurOutil(f"actif_ajoute doit être l'un de {ADDABLE}.")
        if not 0 <= part_ajoutee <= 0.3:
            raise ErreurOutil("part_ajoutee doit être entre 0 et 0.3.")
        if not 0 <= part_actions <= 1:
            raise ErreurOutil("part_actions doit être entre 0 et 1.")
        if reequilibrage not in pf.REBALANCE:
            raise ErreurOutil(f"reequilibrage doit être l'un de {list(pf.REBALANCE)}.")
        if not 0 <= frais <= 0.02:
            raise ErreurOutil("frais doit être entre 0 et 0.02.")

        simple = self._wide("simple_return")
        base = {k: v for k, v in {"SPY": part_actions, "TLT": 1 - part_actions}.items() if v > 0}
        weights = pf.mix(base, {actif_ajoute: part_ajoutee})
        window = simple[list(set(base) | {actif_ajoute, "BIL"})].dropna()
        if annee_debut is not None:
            window = window.loc[str(int(annee_debut)):]
        if len(window) < 252:
            raise ErreurOutil("Moins d'un an de données après cette date de départ : choisir une année plus ancienne.")

        rebalance = pf.REBALANCE[reequilibrage]
        sans = pf.evaluate(pf.backtest(window, base, rebalance, frais)["valeur"], window["BIL"])
        avec = pf.evaluate(pf.backtest(window, weights, rebalance, frais)["valeur"], window["BIL"])
        indicateurs = ["rendement_annuel", "volatilite", "sharpe", "pire_baisse"]
        out = {
            "periode": [_json_value(window.index[0]), _json_value(window.index[-1])],
            "poids_avec_ajout": {k: round(v, 4) for k, v in weights.items()},
            "sans_ajout": {k: _json_value(sans[k]) for k in indicateurs},
            "avec_ajout": {k: _json_value(avec[k]) for k in indicateurs},
            "note": "rendement_annuel, volatilite et pire_baisse sont des fractions (0.05 = 5 %).",
        }
        if part_ajoutee > 0:
            risk = pf.risk_contribution(window, weights)
            out["part_du_risque_actif_ajoute"] = _json_value(risk[actif_ajoute])
        return out

    # --- Krachs ---

    def lister_krachs(self, seuil: float = 0.1) -> Dict[str, Any]:
        if not 0.05 <= seuil <= 0.5:
            raise ErreurOutil("seuil doit être entre 0.05 et 0.5.")
        prices = self._wide("price")
        episodes = m.drawdown_episodes(prices["SPX"].dropna(), threshold=-seuil)
        krachs = []
        for ep in episodes.itertuples():
            during = m.performance_during(prices, ep.sommet, ep.point_bas)
            krachs.append({
                "sommet": _json_value(ep.sommet),
                "point_bas": _json_value(ep.point_bas),
                "retour_au_sommet": _json_value(ep.retour_au_sommet) if pd.notna(ep.retour_au_sommet) else None,
                "baisse_spx": _json_value(ep.baisse),
                "variation_par_actif": {k: _json_value(v) for k, v in during.dropna().items()},
            })
        return {"seuil": seuil, "krachs": krachs,
                "note": "Variations en fractions (−0.34 = −34 %), du sommet au point bas du S&P 500."}

    # --- Graphiques ---

    def tracer_graphique(self, sql: str, type: str, titre: str, unite: str) -> Dict[str, Any]:
        if type not in ("ligne", "barres") or unite not in ("pct", "money", "num"):
            raise ErreurOutil("type doit être ligne ou barres, unite pct, money ou num.")
        df = self._sql(sql, 20000)
        if df.empty or df.shape[1] < 2:
            raise ErreurOutil("Le résultat doit avoir au moins 2 colonnes et une ligne.")
        if df.shape[1] == 3 and not pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
            df = df.pivot_table(index=df.columns[0], columns=df.columns[1], values=df.columns[2], aggfunc="first")
        else:
            df = df.set_index(df.columns[0])
        df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
        if df.empty:
            raise ErreurOutil("Aucune colonne numérique à tracer.")
        if len(df) > 2000:
            raise ErreurOutil("Plus de 2000 points : agréger (par semaine ou par mois) avant de tracer.")
        if type == "ligne":
            try:
                df.index = pd.to_datetime(df.index)
            except (ValueError, TypeError):
                pass
            # Une série sur son propre calendrier (bourse fermée le week-end) aurait des trous :
            # on prolonge le dernier prix connu, seulement entre deux valeurs existantes.
            df = df.sort_index().ffill(limit_area="inside")
        self.graphiques.append(Graphique(type, titre, unite, df))
        return {"ok": True, "series": [str(c) for c in df.columns], "points": len(df),
                "note": "Le graphique est affiché à l'utilisateur sous la réponse."}

    # --- Appel générique ---

    def appeler(self, nom: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute un outil par son nom. Les erreurs reviennent au modèle sous forme de texte."""
        fonctions = {t["name"]: getattr(self, t["name"]) for t in TOOLS}
        if nom not in fonctions:
            return {"erreur": f"Outil inconnu : {nom}."}
        try:
            return fonctions[nom](**arguments)
        except ErreurOutil as e:
            return {"erreur": str(e)}
        except TypeError as e:
            return {"erreur": f"Paramètres invalides : {e}"}
        except Exception as e:  # erreur imprévue : le modèle peut reformuler, l'app ne plante pas
            return {"erreur": f"Erreur pendant le calcul : {type(e).__name__}: {e}"}
