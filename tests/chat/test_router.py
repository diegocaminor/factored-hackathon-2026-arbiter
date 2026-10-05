import pytest
from fastapi.testclient import TestClient

from app.chat.router import get_chat_service
from app.chat.schemas import Intent
from app.chat.service import ChatService
from app.main import app
from app.nba.router import get_nba_service
from tests.chat.fakes import FakeChatModel
from tests.nba.fakes import write_artifact_files

BODY = {"customer_id": "CLI-ACTION", "messages": [{"role": "user", "content": "Yes, send it"}]}


@pytest.fixture
def fake_model():
    return FakeChatModel(intent=Intent.CONFIRM, reply="Done!")


@pytest.fixture
def client(nba_service, execution_service, fake_model):
    # No `with`: the lifespan (real artifact loading) is not triggered.
    service = ChatService(nba_service, execution_service, fake_model)
    app.dependency_overrides[get_nba_service] = lambda: nba_service
    app.dependency_overrides[get_chat_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_turn_contract(client):
    response = client.post("/agent/chat", json=BODY)

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "CLI-ACTION",
        "reply": "Done!",
        "intent": "CONFIRM",
        "action_taken": "OFFER_CONFIRMED",
        "execution_result": {
            "status": "SIMULATED_SENT",
            "customer_id": "CLI-ACTION",
            "product": "Cuenta Ahorro",
            "channel": "Email",
            "provider_message_id": "demo-CLI-ACTION-Email",
        },
    }


def test_unknown_customer_returns_404(client, fake_model):
    response = client.post("/agent/chat", json={**BODY, "customer_id": "CLI-MISSING"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found: CLI-MISSING"}
    assert fake_model.calls == []


def test_classification_failure_returns_502(client, fake_model, offer_sender):
    fake_model.fail_on = {"classify"}

    response = client.post("/agent/chat", json=BODY)

    assert response.status_code == 502
    assert offer_sender.sent == []


@pytest.mark.parametrize(
    "body",
    [
        [1, 2, 3],
        {"customer_id": "CLI-ACTION", "messages": [{"role": "assistant", "content": "Hi"}]},
    ],
    ids=["not-an-object", "last-not-user"],
)
def test_invalid_body_returns_422(client, fake_model, body):
    response = client.post("/agent/chat", json=body)

    assert response.status_code == 422
    assert fake_model.calls == []


def test_chat_is_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "post" in paths["/agent/chat"]


def test_unconfigured_chat_returns_503_and_rest_keeps_working(nba_service, monkeypatch):
    monkeypatch.setattr(app.state, "chat_service", None, raising=False)
    app.dependency_overrides[get_nba_service] = lambda: nba_service
    try:
        client = TestClient(app)
        chat = client.post("/agent/chat", json=BODY)
        health = client.get("/health")
        nba = client.get("/customers/CLI-ACTION/next-best-action")
    finally:
        app.dependency_overrides.clear()

    assert chat.status_code == 503
    assert "unavailable" in chat.json()["detail"]
    assert health.status_code == 200
    assert nba.status_code == 200


def test_startup_without_key_disables_chat(tmp_path, monkeypatch):
    write_artifact_files(tmp_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with TestClient(app) as client:
        assert app.state.chat_service is None
        assert client.post("/agent/chat", json=BODY).status_code == 503
        assert client.get("/health").status_code == 200


def test_startup_with_key_enables_chat(tmp_path, monkeypatch):
    write_artifact_files(tmp_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setenv("CHAT_MODEL", "gpt-6-luna")

    with TestClient(app):
        service = app.state.chat_service
        assert isinstance(service, ChatService)
        assert service._nba is app.state.nba_service
        assert service._execution is app.state.execution_service
        assert service._model._model == "gpt-6-luna"
