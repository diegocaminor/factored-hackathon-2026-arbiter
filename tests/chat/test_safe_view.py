import json

import pytest

from app.chat.safe_view import build_safe_view, safe_outcome
from app.execution.adapters import SimulatedHandoffQueue, SimulatedOfferSender

ALLOWED_KEYS = {"has_offer", "product", "product_summary", "channel", "country", "outcome"}
FORBIDDEN_TOKENS = (
    "propensity",
    "expected_value",
    "expected_conversion_value",
    "estimated_send_cost",
    "historical_support",
    "candidates",
    "decision",
    "ACTION",
    "accepts_marketing",
    "segment",
    "provider_message_id",
    "sales-assistance",
)


def engine_numbers(recommendation):
    values = (
        recommendation.propensity,
        recommendation.expected_conversion_value,
        recommendation.estimated_send_cost,
        recommendation.expected_value,
        recommendation.historical_support,
    )
    return [str(value) for value in values if value is not None]


def test_action_view_carries_offer_fields(nba_service):
    view = build_safe_view(nba_service.recommend("CLI-ACTION"))

    assert view.has_offer is True
    assert view.product == "Cuenta Ahorro"
    assert view.product_summary
    assert view.channel == "Email"
    assert view.country == "Chile"


@pytest.mark.parametrize("customer_id", ["CLI-CONSENT", "CLI-NEGATIVE", "CLI-UNSUPPORTED"])
def test_no_action_view_has_no_offer(nba_service, customer_id):
    view = build_safe_view(nba_service.recommend(customer_id))

    assert view.has_offer is False
    assert view.product is None
    assert view.product_summary is None
    assert view.channel is None


@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT", "CLI-NEGATIVE"])
def test_serialized_view_contains_only_safe_fields(nba_service, customer_id):
    recommendation = nba_service.recommend(customer_id, include_candidates=True)
    serialized = build_safe_view(recommendation).model_dump_json()

    assert set(json.loads(serialized)) == ALLOWED_KEYS
    for token in FORBIDDEN_TOKENS:
        assert token not in serialized
    for number in engine_numbers(recommendation):
        assert number not in serialized


def test_outcomes_omit_identifiers():
    sent = safe_outcome(SimulatedOfferSender().send("CLI-ACTION", "Seguro", "Email"))
    handoff = safe_outcome(SimulatedHandoffQueue().create("CLI-ACTION", "reason"))

    assert sent.model_dump() == {"type": "offer_sent", "channel": "Email"}
    assert handoff.model_dump() == {"type": "advisor_requested", "channel": None}
