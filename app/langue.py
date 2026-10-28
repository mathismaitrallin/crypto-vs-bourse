"""Langue du dashboard : français par défaut, anglais avec ?lang=en dans l'adresse.

La langue est relue dans l'adresse à chaque appel : elle est propre à chaque visiteur, même quand
plusieurs personnes utilisent le dashboard en même temps dans deux langues différentes.
"""
import numpy as np
import pandas as pd
import streamlit as st

MISSING = "–"


def langue() -> str:
    return "en" if st.query_params.get("lang") == "en" else "fr"


def tr(fr: str, en: str) -> str:
    """Texte dans la langue du visiteur."""
    return en if langue() == "en" else fr


def selecteur_langue(conteneur=st) -> None:
    """Boutons FR | EN. Le choix est écrit dans l'adresse : un lien partagé garde la langue."""
    actuelle = langue()
    choix = conteneur.radio("Langue / Language", ["FR", "EN"], index=0 if actuelle == "fr" else 1,
                            horizontal=True, label_visibility="collapsed")
    if choix.lower() != actuelle:
        st.query_params["lang"] = choix.lower()
        st.rerun()


# --- Nombres et dates : 5,2 % / 1 234,5 $ / 28/10/2026 en français, 5.2% / $1,234.5 / Oct 28, 2026 en anglais ---

def _local(text: str) -> str:
    """Séparateurs d'un nombre écrit à l'anglaise (1,234.5) convertis si besoin (1 234,5)."""
    if langue() == "en":
        return text
    return text.replace(",", " ").replace(".", ",")


def pct(value: float, decimals: int = 1, sign: bool = False) -> str:
    if pd.isna(value):
        return MISSING
    text = f"{value:{'+' if sign else ''}.{decimals}%}"
    return text if langue() == "en" else _local(text).replace("%", " %")


def num(value: float, decimals: int = 2, sign: bool = False) -> str:
    if pd.isna(value):
        return MISSING
    return _local(f"{value:{'+' if sign else ''}.{decimals}f}")


def money(text: str) -> str:
    """Ajoute le symbole du dollar à un montant déjà formaté : 1 234 $ / $1,234."""
    return f"${text}" if langue() == "en" else f"{text} $"


def dollars(value: float) -> str:
    """Prix en dollars, avec assez de décimales pour les jetons à quelques millionièmes de dollar."""
    if pd.isna(value):
        return MISSING
    if value >= 1:
        return money(_local(f"{value:,.2f}"))
    decimals = max(2, 3 - int(np.floor(np.log10(value))))
    return money(_local(f"{value:.{decimals}f}"))


def big_dollars(value: float) -> str:
    """Montant en milliards ou millions : 2,1 Md $ / $2.1B."""
    if pd.isna(value):
        return MISSING
    billions = value >= 1e9
    amount = _local(f"{value / (1e9 if billions else 1e6):,.{1 if billions else 0}f}")
    if langue() == "en":
        return f"${amount}{'B' if billions else 'M'}"
    return f"{amount} {'Md' if billions else 'M'} $"


def rang(n: float) -> str:
    """Place dans un classement : 1er, 2e / 1st, 2nd."""
    if pd.isna(n):
        return MISSING
    n = int(n)
    if langue() != "en":
        return "1er" if n == 1 else f"{n}e"
    suffixe = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffixe}"


def date(jour: pd.Timestamp) -> str:
    """28/10/2026 / Oct 28, 2026."""
    return f"{jour:%b} {jour.day}, {jour.year}" if langue() == "en" else f"{jour:%d/%m/%Y}"
