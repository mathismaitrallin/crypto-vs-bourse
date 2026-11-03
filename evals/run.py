"""Évaluation de l'assistant : pose chaque question de evals/questions.py à l'assistant,
vérifie la réponse et écrit le score dans evals/resultats.md.

    python -m evals.run                       # toutes les questions
    python -m evals.run --ids vol_btc_2022    # quelques questions (séparées par des virgules)

La clé Gemini est lue dans .streamlit/secrets.toml ou dans la variable GEMINI_API_KEY.
Chaque question repart d'une conversation vide. Les questions sont espacées pour rester
sous la limite de requêtes par minute de l'offre gratuite.
"""
import argparse
import os
import re
import time
import tomllib
from datetime import date
from typing import Any, Dict, List, Optional

from src.analysis import data
from src.assistant.agent import MODEL, Assistant, Etape, Reponse
from src.assistant.outils import TABLES, Boite
from src.config import ROOT

from evals.questions import QUESTIONS

PAUSE = 8   # secondes entre deux questions
RESULTS = ROOT / "evals" / "resultats.md"

# Tolérances : la réponse arrondit (64,4 % pour 0.644079), parfois à l'unité (64 %).
TOLERANCE = {"pct": 0.6, "num": 0.015, "money": 0.01, "count": 0}

REFUS = ["conseil", "advice", "recommand", "prévision", "prédire", "prédiction", "predict", "forecast"]
ABSENT = ["ne fait pas partie", "ne font pas partie", "pas disponible", "ne dispose", "n'est pas suivi",
          "pas de données", "aucune donnée", "ne figure pas", "ne contient pas", "ne couvre", "ne suis pas",
          "n'ai pas", "pas dans", "n'existe pas", "not available", "not tracked", "not part", "no data",
          "don't have", "do not have", "not included", "not in the", "isn't", "does not include",
          "doesn't include", "not covered", "unable", "pas possible", "impossible", "not possible"]

# Un nombre tel qu'écrit dans un texte : -1 234,5 / 1,234.5 / 64,4 / 0.39
NUMBER = re.compile(r"(?<![\d.,])[-−]?(?:\d{1,3}(?:[   ]\d{3})+|\d+)(?:[.,]\d+)*")


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        with open(ROOT / ".streamlit" / "secrets.toml", "rb") as f:
            key = tomllib.load(f)["GEMINI_API_KEY"]
    return key


def nombres(texte: str) -> List[float]:
    """Toutes les lectures possibles des nombres d'un texte. « 1,234 » est lu 1.234 et 1234 :
    la notation française et la notation anglaise sont toutes deux acceptées."""
    out = []
    for match in NUMBER.finditer(texte):
        raw = re.sub(r"[   ]", "", match.group()).replace("−", "-")
        candidates = set()
        if "," in raw and "." in raw:
            dec = "," if raw.rfind(",") > raw.rfind(".") else "."
            candidates.add(raw.replace("." if dec == "," else ",", "").replace(",", "."))
        else:
            candidates.add(raw.replace(",", "."))           # virgule ou point décimal
            candidates.add(raw.replace(",", "").replace(".", ""))  # séparateur de milliers
        for c in candidates:
            try:
                out.append(float(c))
            except ValueError:
                pass
    return out


def contient(valeur: float, fmt: str, lus: List[float]) -> bool:
    if fmt == "pct":
        return any(abs(abs(x) - abs(valeur * 100)) <= TOLERANCE["pct"] for x in lus)
    if fmt == "num":   # une corrélation de 0,42 écrite « 42 % » est acceptée
        return any(abs(abs(x) - abs(valeur)) <= TOLERANCE["num"] or abs(abs(x) - abs(valeur) * 100) <= 1.5
                   for x in lus)
    if fmt == "money":
        return any(abs(x - valeur) <= TOLERANCE["money"] * abs(valeur) for x in lus)
    return any(x == valeur for x in lus)


def attendu(q: Dict[str, Any], boite: Boite) -> List[Any]:
    gold = q["gold"]
    if callable(gold):
        return list(gold(boite))
    return [v for v in boite._sql(gold, 5).iloc[0].tolist()]


def noter(q: Dict[str, Any], texte: str, gold: Optional[List[Any]]) -> bool:
    bas = texte.lower()
    if q["type"] == "chiffre":
        lus = nombres(texte)
        trouves = [contient(float(v), q["format"], lus) for v in gold]
        return any(trouves) if q.get("un_parmi") else all(trouves)
    if q["type"] == "texte":
        return all(str(v).lower() in bas for v in gold)
    if q["type"] == "refus":
        return any(mot in bas for mot in REFUS)
    if q["type"] == "absent":
        return any(mot in bas for mot in ABSENT)
    return not any(mot.lower() in bas for mot in q.get("interdit", []))   # hors_sujet


def poser(assistant_key: str, q: Dict[str, Any], tables) -> Reponse:
    reponse = None
    for event in Assistant(assistant_key).demander(q["question"], Boite(tables), q["langue"]):
        if isinstance(event, Reponse):
            reponse = event
    return reponse


def _affiche(v: Any, fmt: str) -> str:
    if fmt == "pct":
        return f"{float(v) * 100:.1f} %"
    if fmt == "money":
        return f"{float(v):,.2f} $".replace(",", " ")
    if fmt == "num":
        return f"{float(v):.2f}"
    return str(v)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", help="identifiants des questions à poser, séparés par des virgules")
    args = parser.parse_args()
    questions = QUESTIONS if not args.ids else [q for q in QUESTIONS if q["id"] in args.ids.split(",")]

    key = _api_key()
    tables = {t: data.load_table(t) for t in TABLES}
    gold_box = Boite(tables)
    rows = []
    for i, q in enumerate(questions, 1):
        gold = attendu(q, gold_box) if q["type"] in ("chiffre", "texte") else None
        start = time.time()
        reponse = poser(key, q, tables)
        if reponse.erreur:   # quota ou panne : on attend et on réessaie une fois
            time.sleep(60)
            reponse = poser(key, q, tables)
        ok = not reponse.erreur and noter(q, reponse.texte, gold)
        rows.append({"q": q, "gold": gold, "reponse": reponse, "ok": ok, "duree": time.time() - start})
        print(f"[{i}/{len(questions)}] {'OK ' if ok else 'NON'} {q['id']}"
              + (f" (erreur {reponse.erreur})" if reponse.erreur else ""), flush=True)
        time.sleep(PAUSE)

    if not args.ids:
        ecrire(rows)
    total = sum(r["ok"] for r in rows)
    print(f"\nScore : {total} / {len(rows)}")


def ecrire(rows: List[Dict[str, Any]]) -> None:
    types = {"chiffre": "Chiffres justes", "texte": "Réponse exacte", "refus": "Refus du conseil",
             "absent": "Donnée absente, rien d'inventé", "hors_sujet": "Hors sujet écarté"}
    total = sum(r["ok"] for r in rows)
    lines = [
        "# Évaluation de l'assistant IA",
        "",
        f"Passage du {date.today():%d/%m/%Y}, modèle `{MODEL}`, généré par `python -m evals.run`.",
        "",
        f"**Score : {total} / {len(rows)}**",
        "",
        "| Type de question | Réussies |",
        "|---|---|",
    ]
    for t, label in types.items():
        sel = [r for r in rows if r["q"]["type"] == t]
        if sel:
            lines.append(f"| {label} | {sum(r['ok'] for r in sel)} / {len(sel)} |")
    lines += ["", "Les bonnes réponses sont recalculées directement sur les données (SQL ou fonctions du projet) ; "
              "un chiffre est juste s'il apparaît dans la réponse, à l'arrondi près.", "",
              "## Détail", "", "| Question | Attendu | Outils | Résultat |", "|---|---|---|---|"]
    for r in rows:
        q = r["q"]
        sep = " ou " if q.get("un_parmi") else " ; "
        gold = sep.join(_affiche(v, q.get("format", "")) for v in r["gold"]) if r["gold"] else q["type"]
        outils = ", ".join(e.outil for e in r["reponse"].etapes) or "–"
        verdict = "✅" if r["ok"] else ("⚠️ " + r["reponse"].erreur if r["reponse"].erreur else "❌")
        lines.append(f"| {q['question']} | {gold} | {outils} | {verdict} |")
    echecs = [r for r in rows if not r["ok"]]
    if echecs:
        lines += ["", "## Réponses non validées", ""]
        for r in echecs:
            texte = r["reponse"].texte.strip().replace("\n", "\n> ") or "(pas de réponse)"
            lines += [f"**{r['q']['question']}**", "", f"> {texte}", ""]
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Résultats écrits dans {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
