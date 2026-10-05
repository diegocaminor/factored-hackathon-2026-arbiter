from app.execution.adapters import (
    DEFAULT_HANDOFF_REASON,
    SimulatedHandoffQueue,
    SimulatedOfferSender,
)
from app.execution.schemas import ConfirmResponse, HandoffRequest, HandoffResponse


def test_simulated_send_payload():
    delivery = SimulatedOfferSender().send("CLI-X", "Tarjeta Crédito", "Push")

    assert delivery.model_dump() == {
        "status": "SIMULATED_SENT",
        "customer_id": "CLI-X",
        "product": "Tarjeta Crédito",
        "channel": "Push",
        "provider_message_id": "demo-CLI-X-Push",
    }


def test_provider_message_id_replaces_spaces():
    delivery = SimulatedOfferSender().send("CLI X", "Seguro", "In App")

    assert delivery.provider_message_id == "demo-CLI-X-In-App"


def test_simulated_send_is_deterministic():
    sender = SimulatedOfferSender()

    assert sender.send("CLI-X", "Seguro", "SMS") == sender.send("CLI-X", "Seguro", "SMS")


def test_simulated_handoff_payload():
    handoff = SimulatedHandoffQueue().create("CLI-X", "Needs an advisor")

    assert handoff.model_dump() == {
        "status": "HANDOFF_CREATED",
        "customer_id": "CLI-X",
        "reason": "Needs an advisor",
        "queue": "sales-assistance",
    }


def test_default_reason_matches_agent():
    assert DEFAULT_HANDOFF_REASON == "Customer did not confirm automated execution."


def test_schemas_render():
    confirm = ConfirmResponse.model_json_schema()
    handoff = HandoffResponse.model_json_schema()
    request = HandoffRequest.model_json_schema()

    assert confirm["properties"]["status"]["const"] == "SIMULATED_SENT"
    assert set(confirm["required"]) == {
        "status",
        "customer_id",
        "product",
        "channel",
        "provider_message_id",
    }
    assert handoff["properties"]["status"]["const"] == "HANDOFF_CREATED"
    assert "reason" not in request.get("required", [])
