import json

import pytest

from app.nba.schemas import NextBestActionResponse
from app.nba.service import CustomerNotFound

from tests.nba.fakes import CHILE_PROBABILITIES

ECONOMIC_FIELDS = (
    "product",
    "channel",
    "propensity",
    "expected_conversion_value",
    "estimated_send_cost",
    "expected_value",
    "historical_support",
)


def strict_json(response):
    return json.loads(
        json.dumps(response.model_dump(mode="json"), allow_nan=False),
        parse_constant=lambda c: pytest.fail(f"non-finite constant {c}"),
    )


def test_action_recommendation(nba_service):
    response = nba_service.recommend("CLI-ACTION")

    assert response.customer_id == "CLI-ACTION"
    assert response.country == "Chile"
    assert response.decision == "ACTION"
    assert response.product == "Cuenta Ahorro"
    assert response.channel == "Email"
    assert response.propensity == pytest.approx(0.10)
    assert response.expected_conversion_value == 1000.0
    assert response.estimated_send_cost == 1.0
    assert response.expected_value == pytest.approx(99.0)
    assert response.historical_support == 500
    assert response.candidates is None


def test_has_customer(nba_service, stub_model):
    assert nba_service.has_customer("CLI-ACTION")
    assert not nba_service.has_customer("CLI-MISSING")
    assert stub_model.calls == 0


def test_unknown_customer_does_not_call_model(nba_service, stub_model):
    with pytest.raises(CustomerNotFound, match="CLI-MISSING"):
        nba_service.recommend("CLI-MISSING")

    assert stub_model.calls == 0


def test_no_consent_returns_nulls(nba_service, stub_model):
    response = nba_service.recommend("CLI-CONSENT", include_candidates=True)

    assert response.decision == "NO_ACTION_CONSENT"
    assert all(getattr(response, field) is None for field in ECONOMIC_FIELDS)
    assert response.country == "Chile"
    assert response.candidates == []
    assert stub_model.calls == 0


def test_negative_value_keeps_top_candidate(nba_service):
    response = nba_service.recommend("CLI-NEGATIVE")

    assert response.decision == "NO_ACTION_NEGATIVE_VALUE"
    assert response.product == "Seguro"
    assert response.channel == "SMS"
    probability = CHILE_PROBABILITIES[("Seguro", "SMS")]
    assert response.propensity == pytest.approx(probability)
    assert response.expected_value == pytest.approx(probability * 10.0 - 5.0)
    assert response.historical_support == 300


def test_no_supported_candidates(nba_service):
    response = nba_service.recommend("CLI-UNSUPPORTED", include_candidates=True)

    assert response.decision == "NO_ACTION_NO_SUPPORTED_CANDIDATES"
    assert all(getattr(response, field) is None for field in ECONOMIC_FIELDS)
    assert response.candidates == []


def test_candidates_are_top_five_by_rank(nba_service):
    response = nba_service.recommend("CLI-ACTION", include_candidates=True)

    candidates = response.candidates
    assert [c.rank for c in candidates] == [1, 2, 3, 4, 5]
    assert (candidates[0].product, candidates[0].channel) == (response.product, response.channel)
    assert candidates[0].expected_value == response.expected_value
    assert [c.expected_value for c in candidates] == pytest.approx([99, 89, 79, 69, 59])


def test_non_finite_values_become_null(nba_service):
    response = nba_service.recommend("CLI-NAN", include_candidates=True)

    assert response.decision == "ACTION"
    missing = response.candidates[1]
    assert missing.product == "Inversión"
    assert missing.expected_conversion_value is None
    assert missing.expected_value is None
    strict_json(response)


@pytest.mark.parametrize(
    "customer_id", ["CLI-ACTION", "CLI-CONSENT", "CLI-NEGATIVE", "CLI-UNSUPPORTED", "CLI-NAN"]
)
def test_every_response_is_strict_json(nba_service, customer_id):
    response = nba_service.recommend(customer_id, include_candidates=True)

    payload = strict_json(response)
    assert NextBestActionResponse.model_validate(payload) == response
