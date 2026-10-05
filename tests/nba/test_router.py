import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nba.router import get_nba_service

PATH = "/customers/{customer_id}/next-best-action"


@pytest.fixture
def client(nba_service):
    # No `with`: the lifespan (real artifact loading) is not triggered.
    app.dependency_overrides[get_nba_service] = lambda: nba_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_known_customer_returns_recommendation(client):
    response = client.get(PATH.format(customer_id="CLI-ACTION"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["customer_id"] == "CLI-ACTION"
    assert body["decision"] == "ACTION"
    assert body["product"] == "Cuenta Ahorro"
    assert body["candidates"] is None


def test_unknown_customer_returns_404(client):
    response = client.get(PATH.format(customer_id="CLI-MISSING"))

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found: CLI-MISSING"}


@pytest.mark.parametrize(
    ("customer_id", "decision"),
    [
        ("CLI-CONSENT", "NO_ACTION_CONSENT"),
        ("CLI-NEGATIVE", "NO_ACTION_NEGATIVE_VALUE"),
        ("CLI-UNSUPPORTED", "NO_ACTION_NO_SUPPORTED_CANDIDATES"),
    ],
)
def test_no_action_decisions_return_200(client, customer_id, decision):
    response = client.get(PATH.format(customer_id=customer_id))

    assert response.status_code == 200
    assert response.json()["decision"] == decision


def test_include_candidates(client):
    with_candidates = client.get(
        PATH.format(customer_id="CLI-ACTION"), params={"include_candidates": "true"}
    ).json()
    empty = client.get(
        PATH.format(customer_id="CLI-CONSENT"), params={"include_candidates": "true"}
    ).json()

    assert [c["rank"] for c in with_candidates["candidates"]] == [1, 2, 3, 4, 5]
    assert empty["candidates"] == []


def test_openapi_documents_endpoint(client):
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/customers/{customer_id}/next-best-action"]["get"]

    params = {p["name"]: p for p in operation["parameters"]}
    assert params["customer_id"]["in"] == "path"
    assert params["include_candidates"]["in"] == "query"
    assert params["include_candidates"]["required"] is False

    ok_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert ok_schema == {"$ref": "#/components/schemas/NextBestActionResponse"}
    response_fields = spec["components"]["schemas"]["NextBestActionResponse"]["properties"]
    assert {
        "customer_id",
        "country",
        "decision",
        "product",
        "channel",
        "propensity",
        "expected_conversion_value",
        "estimated_send_cost",
        "expected_value",
        "historical_support",
        "candidates",
    } <= set(response_fields)
    assert "raw" in response_fields["propensity"]["description"].lower()

    not_found = operation["responses"]["404"]["content"]["application/json"]["schema"]
    assert not_found == {"$ref": "#/components/schemas/ErrorResponse"}
