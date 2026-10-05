import dataclasses
import json

import pytest

from app.agent.service import build_agent_service
from app.execution.adapters import DEFAULT_HANDOFF_REASON
from app.nba.service import CustomerNotFound, NBAService

NO_ACTION_CUSTOMERS = [
    ("CLI-CONSENT", "NO_ACTION_CONSENT"),
    ("CLI-UNSUPPORTED", "NO_ACTION_NO_SUPPORTED_CANDIDATES"),
    ("CLI-NEGATIVE", "NO_ACTION_NEGATIVE_VALUE"),
]
RECOMMENDATION_FIELDS = (
    "decision",
    "product",
    "channel",
    "propensity",
    "expected_conversion_value",
    "estimated_send_cost",
    "expected_value",
    "historical_support",
)


def test_confirmed_action_completes(agent_service):
    response = agent_service.run("CLI-ACTION", user_confirmed=True)

    assert response.status == "COMPLETED"
    assert response.consent_required is True
    assert response.product_details.name == "Cuenta Ahorro"
    assert response.execution_result.status == "SIMULATED_SENT"
    assert response.execution_result.product == "Cuenta Ahorro"
    assert response.execution_result.channel == "Email"
    assert response.execution_result.provider_message_id == "demo-CLI-ACTION-Email"


def test_unconfirmed_action_hands_off(agent_service):
    response = agent_service.run("CLI-ACTION", user_confirmed=False)

    assert response.status == "HANDOFF"
    assert response.execution_result.status == "HANDOFF_CREATED"
    assert response.execution_result.reason == DEFAULT_HANDOFF_REASON
    assert response.execution_result.queue == "sales-assistance"


@pytest.mark.parametrize("user_confirmed", [True, False])
@pytest.mark.parametrize(("customer_id", "decision"), NO_ACTION_CUSTOMERS)
def test_no_action_ends_without_execution(agent_service, customer_id, decision, user_confirmed):
    response = agent_service.run(customer_id, user_confirmed=user_confirmed)

    assert response.status == decision
    assert response.recommendation.decision == decision
    assert response.execution_result is None
    assert decision in response.assistant_message


def test_unknown_customer_does_not_invoke_graph(agent_service, spy_graph):
    with pytest.raises(CustomerNotFound, match="CLI-MISSING"):
        agent_service.run("CLI-MISSING", user_confirmed=True)

    assert spy_graph.invocations == []


@pytest.mark.parametrize(
    "customer_id", ["CLI-ACTION", "CLI-CONSENT", "CLI-NEGATIVE", "CLI-UNSUPPORTED", "CLI-NAN"]
)
def test_recommendation_matches_nba_service(agent_service, nba_service, customer_id):
    agent = agent_service.run(customer_id, user_confirmed=True).recommendation
    nba = nba_service.recommend(customer_id)

    for field in RECOMMENDATION_FIELDS:
        assert getattr(agent, field) == getattr(nba, field), field


@pytest.mark.parametrize("user_confirmed", [True, False])
def test_response_hides_internal_state_and_is_strict_json(agent_service, user_confirmed):
    payload = agent_service.run("CLI-ACTION", user_confirmed).model_dump(mode="json")

    assert "customer_row" not in payload
    assert "ranked_actions" not in payload
    json.dumps(payload, allow_nan=False)


def test_repeated_runs_are_identical(agent_service):
    assert agent_service.run("CLI-ACTION", True) == agent_service.run("CLI-ACTION", True)


def test_threshold_flows_from_metadata(artifacts):
    # Fake Chile actions have 500 historical sends; a 600 threshold excludes all of them.
    strict = dataclasses.replace(artifacts, min_historical_sends=600)
    nba_service = NBAService(strict)
    agent_service = build_agent_service(strict, nba_service)

    agent = agent_service.run("CLI-ACTION", user_confirmed=True)
    nba = nba_service.recommend("CLI-ACTION")

    assert agent.recommendation.decision == "NO_ACTION_NO_SUPPORTED_CANDIDATES"
    assert nba.decision == "NO_ACTION_NO_SUPPORTED_CANDIDATES"
    assert agent.execution_result is None
