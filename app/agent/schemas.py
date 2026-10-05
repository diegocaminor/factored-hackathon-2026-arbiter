from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool

from app.execution.schemas import ConfirmResponse, HandoffResponse
from app.nba.schemas import CURRENCY_NOTE, PROPENSITY_DESCRIPTION, Decision

AgentStatus = Literal[
    "COMPLETED",
    "HANDOFF",
    "NO_ACTION_CONSENT",
    "NO_ACTION_NO_SUPPORTED_CANDIDATES",
    "NO_ACTION_NEGATIVE_VALUE",
]


class AgentRunRequest(BaseModel):
    customer_id: str = Field(description="Customer identifier, e.g. CLI-P21780PQ8D9W.")
    user_confirmed: StrictBool = Field(
        description=(
            "JSON boolean. true executes the simulated offer for an ACTION decision; "
            "false creates a human handoff. Ignored for NO_ACTION decisions."
        )
    )


class AgentRecommendation(BaseModel):
    """Engine output only; the agent never generates or alters these values."""

    decision: Decision
    product: str | None
    channel: str | None
    propensity: float | None = Field(description=PROPENSITY_DESCRIPTION)
    expected_conversion_value: float | None = Field(description=CURRENCY_NOTE)
    estimated_send_cost: float | None = Field(description=CURRENCY_NOTE)
    expected_value: float | None = Field(description=CURRENCY_NOTE)
    historical_support: int | None


class ProductDetails(BaseModel):
    name: str
    summary: str


ExecutionResult = Annotated[ConfirmResponse | HandoffResponse, Field(discriminator="status")]


class AgentRunResponse(BaseModel):
    customer_id: str
    user_confirmed: bool
    status: AgentStatus = Field(
        description="Final workflow state: COMPLETED, HANDOFF, or the NO_ACTION decision."
    )
    recommendation: AgentRecommendation
    consent_required: bool | None = Field(
        description="True when an ACTION offer needs customer confirmation; null otherwise."
    )
    product_details: ProductDetails | None
    execution_result: ExecutionResult | None = Field(
        description="Simulated send or handoff; null for NO_ACTION decisions."
    )
    assistant_message: str = Field(description="Template message built from engine values.")
