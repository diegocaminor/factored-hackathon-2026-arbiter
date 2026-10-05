"""Defense in depth behind the safe view: replies must not name internal concepts.

Fixed replies are produced without the chat model, so they cannot detect the
customer's language; each one carries the same message in Spanish and English.
"""

from __future__ import annotations

import re

from app.chat.safe_view import SafeOutcome

FORBIDDEN_TERMS = (
    "catboost",
    "propensity",
    "expected value",
    "next best action",
    "nba",
    "langgraph",
    "ranking",
    "score",
    "model",
    "algorithm",
    # Spanish equivalents: most customers write in Spanish.
    "propensión",
    "puntuación",
    "puntuaciones",
    "puntaje",
    "modelo",
    "algoritmo",
)
# Optional plural endings so "scores", "modelos", or "puntuaciones" are caught as well.
_FORBIDDEN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in FORBIDDEN_TERMS) + r")(s|es)?\b",
    re.IGNORECASE,
)

SAFE_REPLY = (
    "Lo siento, no puedo ayudarte con eso en este momento. "
    "¿Te gustaría que te conecte con un asesor?\n"
    "Sorry, I can't help with that right now. "
    "Would you like me to connect you with an advisor?"
)


def guard_reply(reply: str) -> str:
    """Return the reply unchanged, or the fixed safe reply if it names an internal term."""
    return SAFE_REPLY if _FORBIDDEN.search(reply) else reply


def fallback_reply(outcome: SafeOutcome) -> str:
    """Fixed reply describing an executed action when the chat model is unavailable."""
    if outcome.type == "offer_sent":
        return (
            f"Listo, te enviamos la oferta por {outcome.channel}.\n"
            f"Done, we sent you the offer via {outcome.channel}."
        )
    return (
        "Listo, un asesor se pondrá en contacto contigo pronto.\n"
        "Done, an advisor will contact you soon."
    )
