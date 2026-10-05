"""Endpoint vs. direct engine calls on the real frozen artifacts (skipped when absent)."""

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nba.loader import load_artifacts
from app.nba.settings import resolve_artifact_paths
from propensity.nba_engine import recommend_next_best_action

PATHS = resolve_artifact_paths()
DEMO_CUSTOMER = "CLI-P21780PQ8D9W"

pytestmark = pytest.mark.skipif(
    not all(path.is_file() for path in PATHS.required()),
    reason=f"NBA artifacts not found under {PATHS.root}",
)


@pytest.fixture(scope="module")
def artifacts():
    return load_artifacts(PATHS)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def no_artifact_reads(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("artifact read after startup")

    monkeypatch.setattr(joblib, "load", fail)
    monkeypatch.setattr(pd, "read_parquet", fail)


def sample_customer_ids(artifacts):
    snapshot = artifacts.customer_snapshot
    id_column = artifacts.customer_id_column
    no_consent = snapshot[
        snapshot["accepts_marketing"].astype(str).str.strip().str.lower().isin(
            {"false", "0", "no", "n"}
        )
    ]
    others = snapshot.sample(n=20, random_state=0)
    return [
        DEMO_CUSTOMER,
        str(no_consent.iloc[0][id_column]),
        *[str(cid) for cid in others[id_column]],
    ]


def engine_result(artifacts, customer_id):
    row = artifacts.customer_snapshot.iloc[artifacts.customer_positions[customer_id]]
    return recommend_next_best_action(
        customer_row=row,
        action_catalog=artifacts.action_catalog,
        model=artifacts.model,
        model_features=list(artifacts.model_features),
        categorical_features=list(artifacts.categorical_features),
        min_historical_sends=artifacts.min_historical_sends,
    )


def test_demo_customer_matches_notebook(client, no_artifact_reads):
    body = client.get(f"/customers/{DEMO_CUSTOMER}/next-best-action").json()

    assert body["decision"] == "ACTION"
    assert body["product"] == "Tarjeta Crédito"
    assert body["channel"] == "Push"
    assert body["propensity"] == pytest.approx(0.008405942144870617, abs=1e-12)
    assert body["expected_value"] == pytest.approx(26.788733259173966, abs=1e-9)


def test_endpoint_matches_engine(client, artifacts, no_artifact_reads):
    decisions = set()
    for customer_id in sample_customer_ids(artifacts):
        result, scored = engine_result(artifacts, customer_id)
        response = client.get(
            f"/customers/{customer_id}/next-best-action", params={"include_candidates": "true"}
        )

        assert response.status_code == 200, customer_id
        body = response.json()
        decisions.add(body["decision"])
        assert body["customer_id"] == customer_id
        assert body["decision"] == result.decision
        assert body["product"] == result.promoted_product
        assert body["channel"] == result.send_channel
        assert body["propensity"] == result.propensity_raw
        assert body["expected_conversion_value"] == result.expected_conversion_value
        assert body["estimated_send_cost"] == result.estimated_send_cost
        assert body["expected_value"] == result.expected_value
        assert body["historical_support"] == result.historical_support

        expected_ranks = scored["rank"].head(5).tolist() if not scored.empty else []
        assert [c["rank"] for c in body["candidates"]] == expected_ranks

    assert {"ACTION", "NO_ACTION_CONSENT"} <= decisions


def test_unknown_customer_returns_404(client, no_artifact_reads):
    response = client.get("/customers/CLI-DOES-NOT-EXIST/next-best-action")

    assert response.status_code == 404


def first_no_consent_customer(artifacts):
    return sample_customer_ids(artifacts)[1]


def test_demo_customer_confirms_simulated_send(client, no_artifact_reads):
    response = client.post(f"/customers/{DEMO_CUSTOMER}/confirm")

    assert response.status_code == 200
    assert response.json() == {
        "status": "SIMULATED_SENT",
        "customer_id": DEMO_CUSTOMER,
        "product": "Tarjeta Crédito",
        "channel": "Push",
        "provider_message_id": f"demo-{DEMO_CUSTOMER}-Push",
    }


def test_no_consent_customer_cannot_confirm_but_can_handoff(client, artifacts, no_artifact_reads):
    customer_id = first_no_consent_customer(artifacts)

    confirm = client.post(f"/customers/{customer_id}/confirm")
    handoff = client.post(f"/customers/{customer_id}/handoff")

    assert confirm.status_code == 409
    assert "NO_ACTION_CONSENT" in confirm.json()["detail"]
    assert handoff.status_code == 200
    assert handoff.json()["status"] == "HANDOFF_CREATED"
    assert handoff.json()["queue"] == "sales-assistance"


def test_execution_endpoints_404_for_unknown_customer(client, no_artifact_reads):
    assert client.post("/customers/CLI-DOES-NOT-EXIST/confirm").status_code == 404
    assert client.post("/customers/CLI-DOES-NOT-EXIST/handoff").status_code == 404
