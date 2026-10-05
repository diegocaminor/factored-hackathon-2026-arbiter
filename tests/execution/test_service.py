import pytest

from app.execution.adapters import DEFAULT_HANDOFF_REASON
from app.execution.service import RecommendationNotActionable
from app.nba.service import CustomerNotFound


def test_confirm_sends_recommended_offer(execution_service, nba_service, offer_sender):
    recommendation = nba_service.recommend("CLI-ACTION")

    delivery = execution_service.confirm("CLI-ACTION")

    assert offer_sender.sent == [("CLI-ACTION", recommendation.product, recommendation.channel)]
    assert delivery.status == "SIMULATED_SENT"
    assert (delivery.product, delivery.channel) == ("Cuenta Ahorro", "Email")
    assert delivery.provider_message_id == "demo-CLI-ACTION-Email"


@pytest.mark.parametrize(
    ("customer_id", "decision"),
    [
        ("CLI-CONSENT", "NO_ACTION_CONSENT"),
        ("CLI-UNSUPPORTED", "NO_ACTION_NO_SUPPORTED_CANDIDATES"),
        ("CLI-NEGATIVE", "NO_ACTION_NEGATIVE_VALUE"),
    ],
)
def test_confirm_rejects_non_action(execution_service, offer_sender, customer_id, decision):
    with pytest.raises(RecommendationNotActionable, match=decision) as excinfo:
        execution_service.confirm(customer_id)

    assert excinfo.value.decision == decision
    assert offer_sender.sent == []


def test_confirm_unknown_customer(execution_service, offer_sender):
    with pytest.raises(CustomerNotFound):
        execution_service.confirm("CLI-MISSING")

    assert offer_sender.sent == []


def test_handoff_unknown_customer(execution_service, handoff_queue):
    with pytest.raises(CustomerNotFound):
        execution_service.handoff("CLI-MISSING")

    assert handoff_queue.created == []


def test_handoff_default_reason(execution_service, handoff_queue):
    handoff = execution_service.handoff("CLI-CONSENT")

    assert handoff_queue.created == [("CLI-CONSENT", DEFAULT_HANDOFF_REASON)]
    assert handoff.status == "HANDOFF_CREATED"
    assert handoff.reason == DEFAULT_HANDOFF_REASON
    assert handoff.queue == "sales-assistance"


def test_handoff_custom_reason(execution_service):
    handoff = execution_service.handoff("CLI-ACTION", "Customer asked for an advisor")

    assert handoff.reason == "Customer asked for an advisor"
