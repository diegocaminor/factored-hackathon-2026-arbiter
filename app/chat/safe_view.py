"""The only data the chat model may see about a customer and the executed action.

Engine values (propensity, economic values, rankings, support), decision codes, and
customer model features are deliberately absent: what is never sent cannot leak.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.execution.schemas import ConfirmResponse, HandoffResponse
from app.nba.schemas import NextBestActionResponse
from propensity.langgraph_nba_agent import get_product_details_tool


class SafeOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["offer_sent", "advisor_requested"]
    channel: str | None = None


class SafeView(BaseModel):
    model_config = ConfigDict(frozen=True)

    has_offer: bool
    product: str | None
    product_summary: str | None
    channel: str | None
    country: str | None
    outcome: SafeOutcome | None = None


def build_safe_view(recommendation: NextBestActionResponse) -> SafeView:
    if recommendation.decision != "ACTION" or recommendation.product is None:
        return SafeView(
            has_offer=False,
            product=None,
            product_summary=None,
            channel=None,
            country=recommendation.country,
        )
    details = get_product_details_tool(recommendation.product)
    return SafeView(
        has_offer=True,
        product=recommendation.product,
        product_summary=details.get("summary"),
        channel=recommendation.channel,
        country=recommendation.country,
    )


def safe_outcome(result: ConfirmResponse | HandoffResponse) -> SafeOutcome:
    """Summarize an execution without identifiers such as message IDs or queue names."""
    if isinstance(result, ConfirmResponse):
        return SafeOutcome(type="offer_sent", channel=result.channel)
    return SafeOutcome(type="advisor_requested")
