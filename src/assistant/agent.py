"""Boucle de conversation avec Gemini : le modèle lit la question, appelle les outils dont
il a besoin, lit leurs résultats, puis rédige la réponse.

La boucle est écrite à la main (sans l'appel automatique des fonctions du SDK) pour
afficher chaque étape dans le dashboard et limiter le nombre d'appels d'outils.
"""
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from google import genai
from google.genai import errors, types

from src.assistant.outils import TOOLS, Boite

# gemini-3.5-flash-lite : gratuit, rapide, et environ 15 requêtes par minute sur l'offre gratuite,
# contre 5 pour gemini-3.5-flash (une question en demande 2 à 5). Modifiable sans toucher au code
# avec la variable d'environnement GEMINI_MODEL.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_TOOL_ROUNDS = 6
TIMEOUT_MS = 60_000   # au-delà, on abandonne plutôt que de laisser l'utilisateur attendre
RETRY_WAITS = [20, 40]  # secondes d'attente avant de réessayer quand la limite par minute est atteinte

SYSTEM = """\
Tu es l'assistant d'un projet d'analyse de données : « La cryptomonnaie est-elle devenue un actif \
comme les autres ? ». Le projet compare le Bitcoin, l'Ethereum et le Solana aux actions, aux \
obligations et à l'or, avec des prix journaliers depuis 2018, et suit chaque jour les \
cryptomonnaies tendance sur CoinGecko.

Règles :
1. Chaque chiffre de ta réponse vient d'un outil. Ne calcule rien de tête et n'utilise pas tes \
connaissances générales pour donner un prix, un rendement ou une date.
2. Donne toujours la période sur laquelle porte un chiffre.
3. N'avance pas d'explication que les données ne montrent pas (technologie, taux d'intérêt, \
liquidité…). Si une explication te semble utile, présente-la clairement comme une hypothèse.
4. Si la donnée n'existe pas dans les tables (autre actif, période avant les données, actualité), \
dis-le simplement, sans inventer, et indique ce que tu peux calculer à la place.
5. Tu ne donnes aucun conseil d'investissement : ni « achetez », ni « vendez », ni prévision de \
prix. Tu peux décrire ce qui s'est passé dans les données, en rappelant que le passé ne prédit \
pas l'avenir. Une demande de conseil se refuse directement, sans appeler d'outil.
6. Tu ne réponds qu'aux questions sur ces marchés et sur ce projet ; pour le reste, redirige \
poliment.
7. Réponds en quelques phrases claires pour un non-spécialiste. \
Écris les pourcentages lisiblement (12,3 % en français, 12.3% en anglais), jamais en fraction.
8. Pour un krach ou une crise, utilise lister_krachs : la variation d'un actif pendant un krach \
se mesure du sommet au point bas du S&P 500.
9. Utilise le moins d'appels d'outils possible (l'offre gratuite limite les requêtes par minute) : \
regroupe tes calculs dans une seule requête SQL quand c'est possible.
10. Ajoute un graphique (tracer_graphique) seulement quand il aide vraiment, par exemple pour \
une évolution dans le temps.
"""

LANGUES = {
    "fr": "\nRéponds en français, pourcentages écrits 12,3 %.",
    "en": "\nAnswer in English, whatever the language of these instructions. Write percentages as 12.3%.",
}


@dataclass
class Etape:
    """Un appel d'outil, pour l'afficher à l'utilisateur."""
    outil: str
    arguments: Dict[str, Any]
    resultat: Dict[str, Any]


@dataclass
class Attente:
    """Limite par minute atteinte : l'assistant patiente avant de réessayer."""
    secondes: int


@dataclass
class Reponse:
    texte: str
    etapes: List[Etape] = field(default_factory=list)
    graphiques: list = field(default_factory=list)
    erreur: Optional[str] = None   # "quota", "cle" ou "service" quand Gemini ne répond pas


def _config() -> types.GenerateContentConfig:
    declarations = [
        types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=t["parameters"])
        for t in TOOLS
    ]
    return types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


class Assistant:
    """Une conversation. `historique` garde les messages échangés, y compris les appels
    d'outils, pour que les questions suivantes puissent s'appuyer sur les précédentes."""

    def __init__(self, api_key: str, model: str = MODEL):
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
        self.model = model
        self.config = _config()
        self.historique: List[types.Content] = []

    def _appel(self, contents: List[types.Content], config: types.GenerateContentConfig):
        """Appelle Gemini. Si la limite par minute de l'offre gratuite est atteinte, patiente
        puis réessaie (en produisant un événement Attente). Renvoie (réponse, erreur)."""
        for attente in RETRY_WAITS + [None]:
            try:
                response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
            except errors.APIError as e:
                if e.code in (429, 503) and attente:
                    yield Attente(attente)
                    time.sleep(attente)
                    continue
                return None, _type_erreur(e)
            except Exception:  # délai dépassé, réseau coupé
                return None, "service"
            if not response.candidates or response.candidates[0].content is None:
                return None, "service"
            return response, None
        return None, "quota"

    def demander(self, question: str, boite: Boite, langue: str = "fr") -> Iterator[Any]:
        """Pose une question. Produit les étapes (Etape, Attente) au fil de l'eau, puis la Reponse finale.

        `langue` : langue choisie dans le dashboard ("fr" ou "en"), imposée à la réponse.
        """
        contents = self.historique + [types.Content(role="user", parts=[types.Part(text=question)])]
        etapes: List[Etape] = []
        config = self.config.model_copy(update={"system_instruction": SYSTEM + LANGUES[langue]})
        for round_ in range(MAX_TOOL_ROUNDS + 1):
            if round_ == MAX_TOOL_ROUNDS:
                # Trop d'appels d'outils : on demande une réponse avec ce qui a déjà été trouvé.
                contents.append(types.Content(role="user", parts=[types.Part(
                    text="Tu as atteint la limite d'appels d'outils : réponds maintenant avec ce que tu as déjà trouvé.")]))
                config = config.model_copy(update={"tool_config": types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="NONE"))})

            response, erreur = yield from self._appel(contents, config)
            if erreur:
                yield Reponse("", etapes, boite.graphiques, erreur)
                return

            calls = response.function_calls or []
            # La réponse du modèle est gardée telle quelle : elle contient les signatures de
            # raisonnement que Gemini exige de retrouver au tour suivant.
            contents.append(response.candidates[0].content)
            if not calls:
                self.historique = contents
                yield Reponse(response.text or "", etapes, boite.graphiques)
                return

            parts = []
            for call in calls:
                arguments = dict(call.args or {})
                resultat = boite.appeler(call.name, arguments)
                etape = Etape(call.name, arguments, resultat)
                etapes.append(etape)
                yield etape
                parts.append(types.Part(function_response=types.FunctionResponse(
                    id=call.id, name=call.name, response=_json_safe(resultat))))
            contents.append(types.Content(role="user", parts=parts))


def _json_safe(value: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(value, default=str))


def _type_erreur(e: "errors.APIError") -> str:
    if e.code == 429:
        return "quota"
    if e.code in (400, 401, 403) and "key" in str(e).lower():
        return "cle"
    return "service"
