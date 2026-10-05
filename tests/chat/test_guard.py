import pytest

from app.chat.guard import FORBIDDEN_TERMS, SAFE_REPLY, fallback_reply, guard_reply
from app.chat.safe_view import SafeOutcome


@pytest.mark.parametrize("term", FORBIDDEN_TERMS)
def test_forbidden_term_triggers_safe_reply(term):
    assert guard_reply(f"This offer was chosen by our {term.upper()} logic.") == SAFE_REPLY


def test_clean_reply_passes_unchanged():
    reply = "Based on the information available about your account, Seguro may be a good fit."

    assert guard_reply(reply) == reply


def test_matches_whole_words_only():
    reply = "Te ayudamos a remodelar tu presupuesto con un buen ranqueo de metas."

    assert guard_reply(reply) == reply


@pytest.mark.parametrize(
    ("reply", "outcome"),
    [
        (SAFE_REPLY, None),
        (fallback_reply(SafeOutcome(type="offer_sent", channel="Email")), "Email"),
        (fallback_reply(SafeOutcome(type="advisor_requested")), None),
    ],
)
def test_fixed_replies_are_bilingual_and_clean(reply, outcome):
    spanish, english = reply.split("\n")

    assert spanish and english
    assert guard_reply(reply) == reply
    if outcome:
        assert outcome in spanish and outcome in english


@pytest.mark.parametrize(
    "term", ["scores", "models", "rankings", "modelos", "puntuaciones", "algoritmos"]
)
def test_plural_forms_trigger_safe_reply(term):
    assert guard_reply(f"I can't share details like {term}.") == SAFE_REPLY
