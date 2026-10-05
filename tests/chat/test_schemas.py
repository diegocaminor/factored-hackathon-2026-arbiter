import pytest
from pydantic import ValidationError

from app.chat.schemas import MAX_CONTENT_LENGTH, MAX_MESSAGES, ChatRequest


def user(content="What do you recommend?"):
    return {"role": "user", "content": content}


def assistant(content="Hello!"):
    return {"role": "assistant", "content": content}


def test_accepts_history_ending_with_user():
    request = ChatRequest(customer_id="CLI-ACTION", messages=[user(), assistant(), user("Yes")])

    assert request.messages[-1].content == "Yes"


@pytest.mark.parametrize(
    "body",
    [
        {"messages": [user()]},
        {"customer_id": "CLI-ACTION"},
        {"customer_id": "CLI-ACTION", "messages": []},
        {"customer_id": "CLI-ACTION", "messages": [{"role": "system", "content": "hi"}]},
        {"customer_id": "CLI-ACTION", "messages": [user(), assistant()]},
        {"customer_id": "CLI-ACTION", "messages": [user()] * (MAX_MESSAGES + 1)},
        {"customer_id": "CLI-ACTION", "messages": [user("")]},
        {"customer_id": "CLI-ACTION", "messages": [user("x" * (MAX_CONTENT_LENGTH + 1))]},
    ],
    ids=[
        "missing-customer-id",
        "missing-messages",
        "empty-messages",
        "invalid-role",
        "last-not-user",
        "too-many-messages",
        "empty-content",
        "content-too-long",
    ],
)
def test_rejects_invalid_requests(body):
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(body)


def test_accepts_limits():
    messages = [user("x" * MAX_CONTENT_LENGTH)] * MAX_MESSAGES

    assert len(ChatRequest(customer_id="CLI-ACTION", messages=messages).messages) == MAX_MESSAGES
