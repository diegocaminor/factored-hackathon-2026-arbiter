import pytest
from fastapi.testclient import TestClient

from app.execution.adapters import DEFAULT_HANDOFF_REASON
from app.execution.router import get_execution_service
from app.main import app
from app.nba.router import get_nba_service

CONFIRM = "/customers/{customer_id}/confirm"
HANDOFF = "/customers/{customer_id}/handoff"


@pytest.fixture
def client(nba_service, execution_service):
    # No `with`: the lifespan (real artifact loading) is not triggered.
    app.dependency_overrides[get_nba_service] = lambda: nba_service
    app.dependency_overrides[get_execution_service] = lambda: execution_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_confirm_action_customer(client):
    recommendation = client.get("/customers/CLI-ACTION/next-best-action").json()

    response = client.post(CONFIRM.format(customer_id="CLI-ACTION"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "SIMULATED_SENT",
        "customer_id": "CLI-ACTION",
        "product": recommendation["product"],
        "channel": recommendation["channel"],
        "provider_message_id": "demo-CLI-ACTION-Email",
    }


@pytest.mark.parametrize(
    ("customer_id", "decision"),
    [
        ("CLI-CONSENT", "NO_ACTION_CONSENT"),
        ("CLI-UNSUPPORTED", "NO_ACTION_NO_SUPPORTED_CANDIDATES"),
        ("CLI-NEGATIVE", "NO_ACTION_NEGATIVE_VALUE"),
    ],
)
def test_confirm_non_action_returns_409(client, offer_sender, customer_id, decision):
    response = client.post(CONFIRM.format(customer_id=customer_id))

    assert response.status_code == 409
    assert decision in response.json()["detail"]
    assert offer_sender.sent == []


def test_confirm_unknown_customer_returns_404(client):
    response = client.post(CONFIRM.format(customer_id="CLI-MISSING"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found: CLI-MISSING"}


def test_repeated_confirm_is_identical(client, offer_sender):
    first = client.post(CONFIRM.format(customer_id="CLI-ACTION"))
    second = client.post(CONFIRM.format(customer_id="CLI-ACTION"))

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(offer_sender.sent) == 2


@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT"])
def test_handoff_any_decision(client, customer_id):
    response = client.post(HANDOFF.format(customer_id=customer_id))

    assert response.status_code == 200
    assert response.json() == {
        "status": "HANDOFF_CREATED",
        "customer_id": customer_id,
        "reason": DEFAULT_HANDOFF_REASON,
        "queue": "sales-assistance",
    }


@pytest.mark.parametrize("payload", [{}, {"reason": None}])
def test_handoff_default_reason_for_empty_payloads(client, payload):
    response = client.post(HANDOFF.format(customer_id="CLI-ACTION"), json=payload)

    assert response.status_code == 200
    assert response.json()["reason"] == DEFAULT_HANDOFF_REASON


def test_handoff_custom_reason(client):
    response = client.post(
        HANDOFF.format(customer_id="CLI-ACTION"),
        json={"reason": "Customer asked for an advisor"},
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "Customer asked for an advisor"


@pytest.mark.parametrize("payload", [{"reason": 123}, ["not", "an", "object"], "text"])
def test_handoff_invalid_body_returns_422(client, handoff_queue, payload):
    response = client.post(HANDOFF.format(customer_id="CLI-ACTION"), json=payload)

    assert response.status_code == 422
    assert handoff_queue.created == []


def test_handoff_unknown_customer_returns_404(client):
    response = client.post(HANDOFF.format(customer_id="CLI-MISSING"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found: CLI-MISSING"}


def test_openapi_documents_execution_endpoints(client):
    spec = client.get("/openapi.json").json()
    confirm = spec["paths"]["/customers/{customer_id}/confirm"]["post"]
    handoff = spec["paths"]["/customers/{customer_id}/handoff"]["post"]

    def schema_ref(operation, code):
        return operation["responses"][code]["content"]["application/json"]["schema"]

    assert schema_ref(confirm, "200") == {"$ref": "#/components/schemas/ConfirmResponse"}
    assert schema_ref(confirm, "404") == {"$ref": "#/components/schemas/ErrorResponse"}
    assert schema_ref(confirm, "409") == {"$ref": "#/components/schemas/ErrorResponse"}
    assert "requestBody" not in confirm

    assert schema_ref(handoff, "200") == {"$ref": "#/components/schemas/HandoffResponse"}
    assert schema_ref(handoff, "404") == {"$ref": "#/components/schemas/ErrorResponse"}
    assert handoff["requestBody"].get("required", False) is False
