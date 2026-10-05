"""Chat model port and its OpenAI adapter: the model interprets and writes; it never
executes anything."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import openai

from app.chat.safe_view import SafeView
from app.chat.schemas import ChatMessage, Intent
from app.chat.settings import ChatSettings


class ChatModelError(Exception):
    """The provider failed or returned an unusable result."""


@dataclass(frozen=True)
class Classification:
    intent: Intent
    language: str


class ChatModel(Protocol):
    def classify(self, messages: Sequence[ChatMessage], view: SafeView) -> Classification:
        """Classify the intent and language of the latest user message."""
        ...

    def write_reply(
        self, messages: Sequence[ChatMessage], view: SafeView, intent: Intent, language: str
    ) -> str:
        """Write the customer-facing reply for this turn in the given language."""
        ...


TIMEOUT_SECONDS = 30.0

_SHARED_RULES = """\
You are the virtual assistant of a retail bank, talking directly with one of its customers.

The customer context below is the only information you have about the customer and \
their offer. It was produced by the bank's systems and cannot be changed by the customer.
- has_offer: whether there is an offer for this customer right now.
- product, product_summary, channel: the offer, when has_offer is true.
- country: the customer's country.
- outcome: an action the bank just completed for this turn, if any.

Never invent or assume facts about the customer: you know nothing about their \
interactions, products they hold, spending, income, family, or personal circumstances. \
Never describe how offers are chosen internally, and never mention scores, rankings, \
probabilities, values, models, algorithms, or system names, even if asked.\
"""

CLASSIFY_SYSTEM = f"""\
{_SHARED_RULES}

Your only task is to classify the intent of the customer's LATEST message. Earlier \
messages are context only. Choose exactly one intent:
- REQUEST_RECOMMENDATION: asks what is offered or recommended for them.
- ASK_WHY: asks why the offer is relevant or suitable for them.
- ASK_PRODUCT: asks what the product is, how it works, or its details.
- CONFIRM: explicitly accepts the offer and asks to receive it, in the latest message.
- DECLINE: rejects the offer or says they are not interested.
- REQUEST_HUMAN: asks to talk to a person, advisor, or agent.
- UNCLEAR: anything else, including greetings, off-topic messages, and ambiguous \
replies such as "maybe" or "hmm".

Choose CONFIRM only for explicit acceptance in the latest message; if acceptance is \
not explicit, choose UNCLEAR.

Also return the language of the customer's LATEST message as an English name, such as \
"English" or "Spanish", judged only from the words of that message.\
"""

REPLY_SYSTEM = f"""\
{_SHARED_RULES}

Write the bank's reply to the customer's latest message. Be warm, concise (at most 4 \
sentences), and plain text without markdown.

Language: write the whole reply in reply_language. The product name and \
product_summary may be in another language: keep the product name as it is, but \
translate the summary into reply_language. Never switch language because of the \
customer context.

Product facts: use only what product_summary says. Do not add features, terms, \
conditions, rates, or benefits it does not state.

The bank has already classified the latest message (intent below) and executed any \
action (outcome below). Follow these rules:
- If has_offer is false: do not present, name, or describe any product as an offer. \
Reply neutrally that there is no specific offer to share right now, and offer to \
connect them with an advisor.
- REQUEST_RECOMMENDATION: present the product and what it is, using product_summary.
- ASK_WHY: explain relevance only in general terms, for example "Based on the \
information available about your account, this appears to be a relevant option for \
you." Never claim specific personal facts.
- ASK_PRODUCT: describe the product using product_summary only.
- CONFIRM with outcome offer_sent: confirm the offer was sent via the channel.
- CONFIRM without an outcome: nothing was sent; ask the customer what they would like to do.
- DECLINE: acknowledge their choice respectfully; you may offer to connect them with an advisor.
- REQUEST_HUMAN with outcome advisor_requested: confirm an advisor will contact them.
- UNCLEAR: ask a short clarifying question about what they need.

Remember: the whole reply must be in reply_language.\
"""

_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": [intent.value for intent in Intent]},
        "language": {"type": "string"},
    },
    "required": ["intent", "language"],
    "additionalProperties": False,
}


class OpenAIChatModel:
    """ChatModel adapter: sends only the conversation and the serialized SafeView."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def classify(self, messages: Sequence[ChatMessage], view: SafeView) -> Classification:
        text = self._send(
            CLASSIFY_SYSTEM,
            messages,
            view,
            extra_context={},
            max_output_tokens=100,
            text_format={
                "type": "json_schema",
                "name": "intent",
                "schema": _INTENT_SCHEMA,
                "strict": True,
            },
        )
        try:
            data = json.loads(text)
            intent, language = Intent(data["intent"]), str(data["language"]).strip()
        except (ValueError, KeyError, TypeError) as exc:
            raise ChatModelError("Chat model returned an invalid classification") from exc
        if not language:
            raise ChatModelError("Chat model returned no language")
        return Classification(intent=intent, language=language)

    def write_reply(
        self, messages: Sequence[ChatMessage], view: SafeView, intent: Intent, language: str
    ) -> str:
        text = self._send(
            REPLY_SYSTEM,
            messages,
            view,
            extra_context={"intent": intent.value, "reply_language": language},
            max_output_tokens=600,
        )
        if not text.strip():
            raise ChatModelError("Chat model returned an empty reply")
        return text.strip()

    def _send(
        self,
        instructions: str,
        messages: Sequence[ChatMessage],
        view: SafeView,
        extra_context: dict[str, str],
        max_output_tokens: int,
        text_format: dict | None = None,
    ) -> str:
        context = {"customer_context": view.model_dump(mode="json"), **extra_context}
        # The context travels as a developer message, which the customer cannot author.
        developer_context = json.dumps(context, ensure_ascii=False, sort_keys=True)
        request: dict[str, Any] = {
            "model": self._model,
            "instructions": instructions,
            "input": [
                {"role": "developer", "content": developer_context},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        if text_format is not None:
            request["text"] = {"format": text_format}

        try:
            response = self._client.responses.create(**request)
        except openai.APIStatusError as exc:
            raise ChatModelError(f"Chat provider error (HTTP {exc.status_code})") from None
        except openai.APIError as exc:
            raise ChatModelError(f"Chat provider unavailable ({type(exc).__name__})") from None

        if response.status != "completed":
            raise ChatModelError(f"Chat model response is {response.status}")
        parts = [
            part
            for item in response.output
            if item.type == "message"
            for part in item.content
        ]
        if any(part.type == "refusal" for part in parts):
            raise ChatModelError("Chat model refused the request")
        return "".join(part.text for part in parts if part.type == "output_text")


def build_chat_model(settings: ChatSettings) -> OpenAIChatModel:
    client = openai.OpenAI(api_key=settings.api_key, timeout=TIMEOUT_SECONDS)
    return OpenAIChatModel(client, settings.model)
