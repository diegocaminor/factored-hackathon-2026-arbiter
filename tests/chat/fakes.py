from app.chat.model import ChatModelError, Classification
from app.chat.schemas import Intent


class FakeChatModel:
    """Scripted chat model that records every payload it would send to a provider."""

    def __init__(
        self, intent=Intent.UNCLEAR, reply="Fake reply.", fail_on=(), language="English"
    ):
        self.intent = intent
        self.language = language
        self.reply = reply
        self.fail_on = set(fail_on)
        self.calls = []

    def _record(self, method, messages, view, intent=None, language=None):
        self.calls.append(
            {
                "method": method,
                "messages": [message.model_dump() for message in messages],
                "view": view,
                "payload": view.model_dump_json()
                + "".join(message.content for message in messages),
                "intent": intent,
                "language": language,
            }
        )
        if method in self.fail_on:
            raise ChatModelError(f"{method} failed")

    def classify(self, messages, view):
        self._record("classify", messages, view)
        return Classification(intent=self.intent, language=self.language)

    def write_reply(self, messages, view, intent, language):
        self._record("write_reply", messages, view, intent, language)
        return self.reply
