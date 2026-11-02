"""Section « Assistant IA » du dashboard : une conversation avec Gemini, qui répond en
interrogeant les données du projet (voir src/assistant/)."""
import os
from typing import Dict, Optional

import pandas as pd
import streamlit as st

import plots
from langue import langue, tr
from src.analysis import data
from src.assistant.agent import Assistant, Attente, Etape, Reponse
from src.assistant.outils import TABLES, Boite

MAX_QUESTIONS = 10   # par visiteur et par session : le quota gratuit de Gemini est partagé
CHART = {"config": {"displayModeBar": False}, "use_container_width": True}

STEP_LABELS = {
    "interroger_donnees": ("🔍 Interroge les données", "🔍 Queries the data"),
    "simuler_portefeuille": ("📊 Simule un portefeuille", "📊 Simulates a portfolio"),
    "lister_krachs": ("📉 Liste les krachs", "📉 Lists the crashes"),
    "tracer_graphique": ("📈 Trace un graphique", "📈 Draws a chart"),
}
EXAMPLES = [
    ("Comment le Bitcoin a-t-il réagi pendant le krach du COVID ?",
     "How did Bitcoin react during the COVID crash?"),
    ("L'Ethereum est-il plus lié au Nasdaq ou au CAC 40 ?",
     "Is Ethereum more tied to the Nasdaq or to the CAC 40?"),
    ("Que se serait-il passé avec 10 % de Solana dans un portefeuille 60/40 ?",
     "What would have happened with 10% Solana in a 60/40 portfolio?"),
    ("Quelle cryptomonnaie a été la plus volatile en 2022 ?",
     "Which cryptocurrency was the most volatile in 2022?"),
]
ERRORS = {
    "quota": ("L'assistant a atteint sa limite gratuite pour le moment. Réessayez dans quelques minutes, "
              "ou demain si la limite du jour est atteinte.",
              "The assistant has reached its free limit for now. Try again in a few minutes, "
              "or tomorrow if the daily limit has been reached."),
    "cle": ("La clé d'API Gemini est invalide.", "The Gemini API key is invalid."),
    "service": ("Gemini ne répond pas pour le moment. Réessayez dans quelques instants.",
                "Gemini is not responding right now. Try again in a moment."),
}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_tables() -> Dict[str, pd.DataFrame]:
    tables = {}
    for name in TABLES:
        try:
            tables[name] = data.load_table(name)
        except Exception:  # table absente d'un ancien export : l'assistant fait sans
            pass
    return tables


def api_key() -> Optional[str]:
    """Clé lue dans les secrets Streamlit (.streamlit/secrets.toml en local), sinon dans l'environnement."""
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # aucun fichier de secrets
        key = None
    key = key or os.environ.get("GEMINI_API_KEY")
    return key if key and key != "colle-ta-cle-ici" else None


def show_steps(etapes) -> None:
    for etape in etapes:
        st.markdown(f"**{tr(*STEP_LABELS.get(etape.outil, (etape.outil, etape.outil)))}**")
        if "sql" in etape.arguments:
            st.code(etape.arguments["sql"], language="sql")
        else:
            st.json(etape.arguments, expanded=False)
        if "erreur" in etape.resultat:
            st.caption(f"⚠️ {etape.resultat['erreur']}")


def show_chart(graphique) -> None:
    st.markdown(f"**{graphique.titre}**")
    if graphique.type == "ligne":
        fig = plots.lines(graphique.donnees, graphique.unite, height=340)
    else:
        df = graphique.donnees.copy()
        df.index = [str(i) for i in df.index]
        fig = plots.bars(df, graphique.unite, height=340)
    st.plotly_chart(fig, **CHART)


def show_answer(message: dict) -> None:
    # Les $ sont échappés : Streamlit lirait sinon le texte entre deux $ comme une formule mathématique.
    st.markdown(message["texte"].replace("$", "\\$"))
    for graphique in message.get("graphiques", []):
        show_chart(graphique)
    if message.get("etapes"):
        n = len(message["etapes"])
        with st.expander(tr(f"Comment j'ai trouvé ({n} étape{'s' if n > 1 else ''})",
                            f"How I found it ({n} step{'s' if n > 1 else ''})")):
            show_steps(message["etapes"])


def render() -> None:
    st.markdown(tr(
        "Posez une question sur les données du projet : l'assistant interroge lui-même la base, lance des "
        "simulations et trace des graphiques. **Les chiffres viennent toujours des données**, et chaque "
        "réponse montre comment elle a été trouvée.",
        "Ask a question about the project's data: the assistant queries the database itself, runs "
        "simulations and draws charts. **The figures always come from the data**, and each answer shows "
        "how it was found.",
    ))
    st.caption(tr(
        f"Propulsé par Gemini 3.5 Flash-Lite (Google), offre gratuite : vos questions sont transmises à Google, ne saisissez "
        f"aucune information personnelle. {MAX_QUESTIONS} questions par visite. Ce n'est pas un conseil d'investissement.",
        f"Powered by Gemini 3.5 Flash-Lite (Google), free tier: your questions are sent to Google, do not enter any personal "
        f"information. {MAX_QUESTIONS} questions per visit. This is not investment advice.",
    ))

    key = api_key()
    if key is None:
        st.info(tr(
            "L'assistant n'est pas configuré : il faut une clé d'API Gemini dans `.streamlit/secrets.toml` "
            "(`GEMINI_API_KEY = \"...\"`), ou dans les secrets Streamlit Cloud.",
            "The assistant is not configured: a Gemini API key is needed in `.streamlit/secrets.toml` "
            "(`GEMINI_API_KEY = \"...\"`), or in the Streamlit Cloud secrets.",
        ))
        return

    state = st.session_state
    if "assistant" not in state:
        state.assistant = Assistant(key)
        state.assistant_messages = []
        state.assistant_questions = 0

    for message in state.assistant_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["texte"])
            else:
                show_answer(message)

    question = None
    if not state.assistant_messages:
        st.markdown(tr("**Exemples :**", "**Examples:**"))
        columns = st.columns(2)
        for i, example in enumerate(EXAMPLES):
            if columns[i % 2].button(tr(*example), key=f"example_{i}", use_container_width=True):
                question = tr(*example)
    elif st.button(tr("Nouvelle conversation", "New conversation"), key="assistant_reset"):
        del state["assistant"]
        st.rerun()

    remaining = MAX_QUESTIONS - state.assistant_questions
    typed = st.chat_input(
        tr("Votre question…", "Your question…") if remaining > 0
        else tr("Limite de questions atteinte pour cette visite", "Question limit reached for this visit"),
        disabled=remaining <= 0, max_chars=500,
    )
    question = question or typed
    if not question or remaining <= 0:
        return

    state.assistant_questions += 1
    state.assistant_messages.append({"role": "user", "texte": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.status(tr("Je cherche dans les données…", "Searching the data…"), expanded=False) as status:
            reponse = None
            for event in state.assistant.demander(question, Boite(load_tables()), langue()):
                if isinstance(event, Attente):
                    status.write(tr(f"⏳ Gemini est très sollicité : nouvel essai dans {event.secondes} s…",
                                    f"⏳ Gemini is busy: retrying in {event.secondes} s…"))
                elif isinstance(event, Etape):
                    status.write(tr(*STEP_LABELS.get(event.outil, (event.outil, event.outil))))
                elif isinstance(event, Reponse):
                    reponse = event
            status.update(label=tr("Terminé", "Done"), state="error" if reponse.erreur else "complete")

        if reponse.erreur:
            state.assistant_questions -= 1   # une panne ne compte pas comme une question
            state.assistant_messages.pop()
            st.warning(tr(*ERRORS[reponse.erreur]))
            return
        message = {"role": "assistant", "texte": reponse.texte, "etapes": reponse.etapes,
                   "graphiques": reponse.graphiques}
        state.assistant_messages.append(message)
        show_answer(message)
    st.rerun()
