from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.execution.schemas import ConfirmResponse, HandoffResponse

MAX_MESSAGES = 20
MAX_CONTENT_LENGTH = 2000


class Intent(StrEnum):
    REQUEST_RECOMMENDATION = "REQUEST_RECOMMENDATION"
    ASK_WHY = "ASK_WHY"
    ASK_PRODUCT = "ASK_PRODUCT"
    CONFIRM = "CONFIRM"
    DECLINE = "DECLINE"
    REQUEST_HUMAN = "REQUEST_HUMAN"
    UNCLEAR = "UNCLEAR"


class ActionTaken(StrEnum):
    NONE = "NONE"
    OFFER_CONFIRMED = "OFFER_CONFIRMED"
    HANDOFF_CREATED = "HANDOFF_CREATED"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)


class ChatRequest(BaseModel):
    customer_id: str = Field(description="Customer identifier, e.g. CLI-P21780PQ8D9W.")
    messages: list[ChatMessage] = Field(
        min_length=1,
        max_length=MAX_MESSAGES,
        description=(
            "Full conversation so far, oldest first; the last message must be from the user. "
            "The service stores nothing between requests."
        ),
    )

    @field_validator("messages")
    @classmethod
    def last_message_is_from_user(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages[-1].role != "user":
            raise ValueError("the last message must have role 'user'")
        return messages


ExecutionResult = Annotated[ConfirmResponse | HandoffResponse, Field(discriminator="status")]


class ChatResponse(BaseModel):
    customer_id: str
    reply: str = Field(description="Customer-facing assistant reply.")
    intent: Intent = Field(description="Intent classified from the latest user message.")
    action_taken: ActionTaken = Field(
        description="Action executed by the service for this turn, if any."
    )
    execution_result: ExecutionResult | None = Field(
        description="Simulated send or handoff when an action ran; null otherwise."
    )
