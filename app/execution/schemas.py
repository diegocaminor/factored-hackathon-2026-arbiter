from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConfirmResponse(BaseModel):
    status: Literal["SIMULATED_SENT"] = Field(
        description="Simulated delivery; no provider was contacted."
    )
    customer_id: str
    product: str
    channel: str
    provider_message_id: str = Field(
        description="Deterministic simulated identifier: demo-{customer_id}-{channel}."
    )


class HandoffRequest(BaseModel):
    reason: str | None = Field(
        default=None,
        description="Why the customer is escalated. Defaults when absent or null.",
    )


class HandoffResponse(BaseModel):
    status: Literal["HANDOFF_CREATED"] = Field(
        description="Simulated handoff; no external system was contacted."
    )
    customer_id: str
    reason: str
    queue: str = Field(description="Human queue that receives the handoff.")
