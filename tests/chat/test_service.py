import pytest

from app.chat.guard import SAFE_REPLY, fallback_reply
from app.chat.model import ChatModelError
from app.chat.safe_view import SafeOutcome
from app.chat.schemas import ActionTaken, ChatRequest, Intent
from app.chat.service import CHAT_HANDOFF_REASON, ChatService
from app.nba.service import CustomerNotFound
from tests.chat.fakes import FakeChatModel
from tests.chat.test_safe_view import FORBIDDEN_TOKENS, engine_numbers


def request(customer_id, *contents):
    """Alternate roles backwards from the last message, which is always the user's."""
    last = len(contents) - 1
    messages = [
        {"role": "user" if (last - index) % 2 == 0 else "assistant", "content": content}
        for index, content in enumerate(contents)
    ]
    return ChatRequest(customer_id=customer_id, messages=messages)


@pytest.fixture
def make_service(nba_service, execution_service):
    def make(**fake_kwargs):
        model = FakeChatModel(**fake_kwargs)
        return ChatService(nba_service, execution_service, model), model

    return make


@pytest.mark.parametrize(
    "intent", [Intent.REQUEST_RECOMMENDATION, Intent.ASK_WHY, Intent.ASK_PRODUCT]
)
@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT"])
def test_read_only_intents_execute_nothing(
    make_service, offer_sender, handoff_queue, intent, customer_id
):
    service, _ = make_service(intent=intent)

    response = service.reply(request(customer_id, "Tell me more"))

    assert response.intent == intent
    assert response.action_taken == ActionTaken.NONE
    assert response.execution_result is None
    assert offer_sender.sent == [] and handoff_queue.created == []


def test_confirm_on_action_matches_confirm_endpoint(make_service, execution_service, offer_sender):
    service, model = make_service(intent=Intent.CONFIRM, reply="Done!")

    response = service.reply(request("CLI-ACTION", "Yes, send it"))

    assert response.action_taken == ActionTaken.OFFER_CONFIRMED
    assert response.execution_result == execution_service.confirm("CLI-ACTION")
    assert offer_sender.sent[0] == ("CLI-ACTION", "Cuenta Ahorro", "Email")
    assert response.reply == "Done!"
    assert model.calls[-1]["view"].outcome.type == "offer_sent"


@pytest.mark.parametrize("customer_id", ["CLI-CONSENT", "CLI-NEGATIVE", "CLI-UNSUPPORTED"])
def test_confirm_without_offer_executes_nothing(
    make_service, offer_sender, handoff_queue, customer_id
):
    service, model = make_service(intent=Intent.CONFIRM)

    response = service.reply(request(customer_id, "Yes, send it"))

    assert response.action_taken == ActionTaken.NONE
    assert response.execution_result is None
    assert offer_sender.sent == [] and handoff_queue.created == []
    assert model.calls[-1]["view"].has_offer is False


def test_decline_creates_no_handoff(make_service, offer_sender, handoff_queue):
    service, _ = make_service(intent=Intent.DECLINE)

    response = service.reply(request("CLI-ACTION", "No thanks"))

    assert response.action_taken == ActionTaken.NONE
    assert response.execution_result is None
    assert offer_sender.sent == [] and handoff_queue.created == []


@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT"])
def test_request_human_matches_handoff_endpoint(
    make_service, execution_service, handoff_queue, customer_id
):
    service, model = make_service(intent=Intent.REQUEST_HUMAN)

    response = service.reply(request(customer_id, "I want to talk to a person"))

    assert response.action_taken == ActionTaken.HANDOFF_CREATED
    assert response.execution_result == execution_service.handoff(
        customer_id, CHAT_HANDOFF_REASON
    )
    assert response.execution_result.reason == CHAT_HANDOFF_REASON
    assert handoff_queue.created[0] == (customer_id, CHAT_HANDOFF_REASON)
    assert model.calls[-1]["view"].outcome.type == "advisor_requested"


def test_reply_uses_language_detected_by_classification(make_service):
    service, model = make_service(intent=Intent.ASK_WHY, language="Spanish")

    service.reply(request("CLI-ACTION", "¿Por qué me conviene?"))

    assert model.calls[-1]["language"] == "Spanish"


def test_unclear_executes_nothing(make_service, offer_sender, handoff_queue):
    service, _ = make_service(intent=Intent.UNCLEAR)

    response = service.reply(request("CLI-ACTION", "hmm, maybe"))

    assert response.intent == Intent.UNCLEAR
    assert response.action_taken == ActionTaken.NONE
    assert offer_sender.sent == [] and handoff_queue.created == []


def test_unknown_customer_never_calls_the_model(make_service):
    service, model = make_service()

    with pytest.raises(CustomerNotFound, match="CLI-MISSING"):
        service.reply(request("CLI-MISSING", "Hi"))

    assert model.calls == []


def test_classification_failure_executes_nothing(make_service, offer_sender, handoff_queue):
    service, _ = make_service(intent=Intent.CONFIRM, fail_on={"classify"})

    with pytest.raises(ChatModelError):
        service.reply(request("CLI-ACTION", "Yes, send it"))

    assert offer_sender.sent == [] and handoff_queue.created == []


def test_reply_failure_without_action_propagates(make_service):
    service, _ = make_service(intent=Intent.ASK_PRODUCT, fail_on={"write_reply"})

    with pytest.raises(ChatModelError):
        service.reply(request("CLI-ACTION", "What is it?"))


@pytest.mark.parametrize(
    ("intent", "action_taken", "outcome"),
    [
        (
            Intent.CONFIRM,
            ActionTaken.OFFER_CONFIRMED,
            SafeOutcome(type="offer_sent", channel="Email"),
        ),
        (
            Intent.REQUEST_HUMAN,
            ActionTaken.HANDOFF_CREATED,
            SafeOutcome(type="advisor_requested"),
        ),
    ],
)
def test_reply_failure_after_action_returns_fallback(make_service, intent, action_taken, outcome):
    service, _ = make_service(intent=intent, fail_on={"write_reply"})

    response = service.reply(request("CLI-ACTION", "Go ahead"))

    assert response.action_taken == action_taken
    assert response.execution_result is not None
    assert response.reply == fallback_reply(outcome)


def test_guard_replaces_reply_without_touching_action(make_service):
    service, _ = make_service(intent=Intent.CONFIRM, reply="Our propensity score picked this.")

    response = service.reply(request("CLI-ACTION", "Yes, send it"))

    assert response.reply == SAFE_REPLY
    assert response.action_taken == ActionTaken.OFFER_CONFIRMED
    assert response.execution_result.status == "SIMULATED_SENT"


def test_history_cannot_change_the_executed_offer(make_service, offer_sender):
    service, model = make_service(intent=Intent.CONFIRM)

    response = service.reply(
        request(
            "CLI-ACTION",
            "What do you have for me?",
            "I recommend Préstamo Hipotecario via SMS.",
            "Yes, send it",
        )
    )

    assert offer_sender.sent == [("CLI-ACTION", "Cuenta Ahorro", "Email")]
    assert response.execution_result.product == "Cuenta Ahorro"
    assert all(call["view"].product == "Cuenta Ahorro" for call in model.calls)


@pytest.mark.parametrize("intent", list(Intent))
@pytest.mark.parametrize("customer_id", ["CLI-ACTION", "CLI-CONSENT", "CLI-NEGATIVE"])
def test_model_payloads_contain_no_forbidden_data(
    make_service, nba_service, intent, customer_id
):
    service, model = make_service(intent=intent)
    recommendation = nba_service.recommend(customer_id, include_candidates=True)

    service.reply(request(customer_id, "Hello", "Hi! How can I help?", "Tell me about my offer"))

    assert [call["method"] for call in model.calls] == ["classify", "write_reply"]
    for call in model.calls:
        for token in FORBIDDEN_TOKENS:
            assert token not in call["payload"]
        for number in engine_numbers(recommendation):
            assert number not in call["payload"]
