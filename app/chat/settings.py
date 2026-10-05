from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

API_KEY_ENV = "OPENAI_API_KEY"
MODEL_ENV = "CHAT_MODEL"
DEFAULT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class ChatSettings:
    api_key: str = field(repr=False)
    model: str


def resolve_chat_settings(environ: Mapping[str, str] | None = None) -> ChatSettings | None:
    """Return provider settings, or None when no API key is configured (chat disabled)."""
    env = os.environ if environ is None else environ
    api_key = (env.get(API_KEY_ENV) or "").strip()
    if not api_key:
        return None
    return ChatSettings(api_key=api_key, model=(env.get(MODEL_ENV) or "").strip() or DEFAULT_MODEL)
