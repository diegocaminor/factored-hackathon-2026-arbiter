import pytest
from fastapi.testclient import TestClient

from app.agent.router import get_agent_service
from app.execution.router import get_execution_service
from app.main import app
from app.nba.router import get_nba_service

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


@pytest.fixture
def client(nba_service, execution_service, agent_service):
    # No `with`: the lifespan (real artifact loading) is not triggered.
    app.dependency_overrides[get_nba_service] = lambda: nba_service
    app.dependency_overrides[get_execution_service] = lambda: execution_service
    app.dependency_overrides[get_agent_service] = lambda: agent_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def run(client, customer_id, user_confirmed):
    return client.post(
        "/agent/run", json={"customer_id": customer_id, "user_confirmed": user_confirmed}
    )


@pytest.mark.parametrize(
    ("customer_id", "user_confirmed", "status"),
    [
        ("CLI-ACTION", True, "COMPLETED"),
        ("CLI-ACTION", False, "HANDOFF"),
        ("CLI-CONSENT", True, "NO_ACTION_CONSENT"),
        ("CLI-UNSUPPORTED", False, "NO_ACTION_NO_SUPPORTED_CANDIDATES"),
        ("CLI-NEGATIVE", True, "NO_ACTION_NEGATIVE_VALUE"),
    ],
)
def test_routing_outcomes(client, customer_id, user_confirmed, status):
    response = run(client, customer_id, user_confirmed)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == status
    assert body["customer_id"] == customer_id
    assert body["user_confirmed"] is user_confirmed


def test_unknown_customer_returns_404(client, spy_graph):
    response = run(client, "CLI-MISSING", True)

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found: CLI-MISSING"}
    assert spy_graph.invocations == []


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"customer_id": "CLI-ACTION"},
        {"user_confirmed": True},
        {"customer_id": "CLI-ACTION", "user_confirmed": "true"},
        {"customer_id": "CLI-ACTION", "user_confirmed": 1},
        ["CLI-ACTION", True],
    ],
)
def test_invalid_request_returns_422(client, spy_graph, payload):
    response = client.post("/agent/run", json=payload)

    assert response.status_code == 422
    assert spy_graph.invocations == []


@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT", "CLI-NEGATIVE", "CLI-NAN"])
def test_recommendation_matches_nba_endpoint(client, customer_id):
    agent = run(client, customer_id, True).json()["recommendation"]
    nba = client.get(f"/customers/{customer_id}/next-best-action").json()

    assert {f: agent[f] for f in RECOMMENDATION_FIELDS} == {f: nba[f] for f in RECOMMENDATION_FIELDS}


def test_confirmed_execution_matches_confirm_endpoint(client):
    agent = run(client, "CLI-ACTION", True).json()
    confirm = client.post("/customers/CLI-ACTION/confirm").json()

    assert agent["execution_result"] == confirm


def test_unconfirmed_execution_matches_handoff_endpoint(client):
    agent = run(client, "CLI-ACTION", False).json()
    handoff = client.post("/customers/CLI-ACTION/handoff").json()

    assert agent["execution_result"] == handoff


def test_repeated_requests_are_identical(client):
    assert run(client, "CLI-ACTION", True).json() == run(client, "CLI-ACTION", True).json()


def test_openapi_documents_agent_endpoint(client):
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/agent/run"]["post"]

    assert operation["requestBody"]["required"] is True
    body_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = spec["components"]["schemas"][body_ref.rsplit("/", 1)[-1]]
    assert set(request_schema["required"]) == {"customer_id", "user_confirmed"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AgentRunResponse"
    }
    assert operation["responses"]["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
