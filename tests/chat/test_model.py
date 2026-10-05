import json
import logging
from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.chat.model import (
    CLASSIFY_SYSTEM,
    REPLY_SYSTEM,
    ChatModelError,
    Classification,
    OpenAIChatModel,
    build_chat_model,
)
from app.chat.safe_view import SafeOutcome, SafeView
from app.chat.schemas import ChatMessage, Intent
from app.chat.settings import ChatSettings, resolve_chat_settings

SECRET = "sk-test-secret"
MODEL = "gpt-4o-mini"
VIEW = SafeView(
    has_offer=True,
    product="Seguro",
    product_summary="Producto de protección financiera.",
    channel="Email",
    country="Chile",
)
MESSAGES = [
    ChatMessage(role="user", content="Hola"),
    ChatMessage(role="assistant", content="¿En qué te ayudo?"),
    ChatMessage(role="user", content="¿Qué me recomiendan?"),
]


def response(*parts, status="completed"):
    message = SimpleNamespace(type="message", content=list(parts))
    return SimpleNamespace(status=status, output=[message])


def text(value):
    return SimpleNamespace(type="output_text", text=value)


def refusal(value="I can't help with that."):
    return SimpleNamespace(type="refusal", refusal=value)


class StubClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.requests = []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def api_request():
    return httpx2.Request("POST", "https://api.openai.com/v1/responses")


def developer_context(request):
    first = request["input"][0]
    assert first["role"] == "developer"
    return json.loads(first["content"])


def test_classify_sends_only_messages_and_safe_view():
    client = StubClient(
        response(text('{"intent": "REQUEST_RECOMMENDATION", "language": " Spanish "}'))
    )

    classification = OpenAIChatModel(client, MODEL).classify(MESSAGES, VIEW)

    request = client.requests[0]
    assert classification == Classification(Intent.REQUEST_RECOMMENDATION, "Spanish")
    assert request["model"] == MODEL
    assert request["instructions"] == CLASSIFY_SYSTEM
    assert request["store"] is False
    assert developer_context(request) == {"customer_context": VIEW.model_dump(mode="json")}
    assert request["input"][1:] == [m.model_dump() for m in MESSAGES]
    schema_format = request["text"]["format"]
    assert schema_format["type"] == "json_schema" and schema_format["strict"] is True
    assert schema_format["schema"]["properties"]["intent"]["enum"] == [i.value for i in Intent]
    assert schema_format["schema"]["required"] == ["intent", "language"]


def test_write_reply_sends_intent_and_outcome():
    client = StubClient(response(text("  Listo, te enviamos la oferta.  ")))
    view = VIEW.model_copy(update={"outcome": SafeOutcome(type="offer_sent", channel="Email")})

    reply = OpenAIChatModel(client, MODEL).write_reply(MESSAGES, view, Intent.CONFIRM, "English")

    request = client.requests[0]
    assert reply == "Listo, te enviamos la oferta."
    assert request["instructions"] == REPLY_SYSTEM
    assert developer_context(request) == {
        "customer_context": view.model_dump(mode="json"),
        "intent": "CONFIRM",
        "reply_language": "English",
    }
    assert "text" not in request


@pytest.mark.parametrize(
    "result",
    [
        response(refusal()),
        response(text('{"intent": "CONF'), status="incomplete"),
        response(text("not json")),
        response(text('{"intent": "BUY_NOW", "language": "English"}')),
        response(text('{"language": "English"}')),
        response(text('{"intent": "CONFIRM"}')),
        response(text('{"intent": "CONFIRM", "language": "  "}')),
    ],
    ids=[
        "refusal",
        "incomplete",
        "invalid-json",
        "unknown-intent",
        "missing-intent",
        "missing-language",
        "blank-language",
    ],
)
def test_unusable_classification_raises(result):
    with pytest.raises(ChatModelError):
        OpenAIChatModel(StubClient(result), MODEL).classify(MESSAGES, VIEW)


@pytest.mark.parametrize(
    "result", [response(text("   ")), response(refusal())], ids=["empty", "refusal"]
)
def test_unusable_reply_raises(result):
    with pytest.raises(ChatModelError):
        OpenAIChatModel(StubClient(result), MODEL).write_reply(
            MESSAGES, VIEW, Intent.ASK_PRODUCT, "English"
        )


@pytest.mark.parametrize(
    "error",
    [
        openai.APIConnectionError(request=api_request()),
        openai.AuthenticationError(
            f"Incorrect API key provided: {SECRET}",
            response=httpx2.Response(401, request=api_request()),
            body=None,
        ),
    ],
    ids=["connection", "authentication"],
)
def test_provider_errors_never_expose_the_key(error, caplog):
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ChatModelError) as raised:
        OpenAIChatModel(StubClient(error=error), MODEL).classify(MESSAGES, VIEW)

    assert SECRET not in str(raised.value)
    assert raised.value.__cause__ is None
    assert SECRET not in caplog.text


def test_settings_hide_the_key():
    settings = resolve_chat_settings({"OPENAI_API_KEY": SECRET})

    assert SECRET not in repr(settings)
    assert settings.model == MODEL


@pytest.mark.parametrize("environ", [{}, {"OPENAI_API_KEY": ""}, {"OPENAI_API_KEY": "  "}])
def test_settings_disabled_without_key(environ):
    assert resolve_chat_settings(environ) is None


def test_settings_read_model_override():
    settings = resolve_chat_settings({"OPENAI_API_KEY": SECRET, "CHAT_MODEL": "gpt-6-luna"})

    assert settings.model == "gpt-6-luna"


def test_build_chat_model_uses_configured_model():
    model = build_chat_model(ChatSettings(api_key=SECRET, model="gpt-6-luna"))

    assert isinstance(model, OpenAIChatModel)
    assert model._model == "gpt-6-luna"
