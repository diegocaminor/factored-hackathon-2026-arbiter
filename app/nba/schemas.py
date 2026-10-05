from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal[
    "ACTION",
    "NO_ACTION_CONSENT",
    "NO_ACTION_NO_SUPPORTED_CANDIDATES",
    "NO_ACTION_NEGATIVE_VALUE",
]

PROPENSITY_DESCRIPTION = (
    "Raw, uncalibrated model score used for ranking. Not a calibrated conversion probability."
)
CURRENCY_NOTE = "Local currency of the customer's country; do not aggregate across countries."


class CandidateAction(BaseModel):
    rank: int = Field(description="Position in the engine ranking, starting at 1.")
    product: str
    channel: str
    propensity: float | None = Field(description=PROPENSITY_DESCRIPTION)
    expected_conversion_value: float | None = Field(description=CURRENCY_NOTE)
    estimated_send_cost: float | None = Field(description=CURRENCY_NOTE)
    expected_value: float | None = Field(
        description=f"propensity * expected_conversion_value - estimated_send_cost. {CURRENCY_NOTE}"
    )
    historical_support: int | None = Field(
        description="Pre-test historical sends backing this action profile."
    )


class NextBestActionResponse(BaseModel):
    customer_id: str
    country: str | None = Field(description="Customer country; defines the currency of values.")
    decision: Decision = Field(
        description="ACTION, or the NO_ACTION reason. All decisions return HTTP 200."
    )
    product: str | None
    channel: str | None
    propensity: float | None = Field(description=PROPENSITY_DESCRIPTION)
    expected_conversion_value: float | None = Field(description=CURRENCY_NOTE)
    estimated_send_cost: float | None = Field(description=CURRENCY_NOTE)
    expected_value: float | None = Field(
        description=f"propensity * expected_conversion_value - estimated_send_cost. {CURRENCY_NOTE}"
    )
    historical_support: int | None = Field(
        description="Pre-test historical sends backing the recommended action profile."
    )
    candidates: list[CandidateAction] | None = Field(
        description="Top ranked scored actions (max 5) when include_candidates=true, else null."
    )


class ErrorResponse(BaseModel):
    detail: str
