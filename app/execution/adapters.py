"""Execution ports and their simulated adapters.

Values mirror the vendored agent tools (propensity.langgraph_nba_agent) so API and
agent payloads stay identical; that module is not imported because it requires LangGraph.
"""

from __future__ import annotations

from typing import Protocol

from app.execution.schemas import ConfirmResponse, HandoffResponse

SIMULATED_SENT = "SIMULATED_SENT"
HANDOFF_CREATED = "HANDOFF_CREATED"
HANDOFF_QUEUE = "sales-assistance"
DEFAULT_HANDOFF_REASON = "Customer did not confirm automated execution."


class OfferSender(Protocol):
    def send(self, customer_id: str, product: str, channel: str) -> ConfirmResponse: ...


class HandoffQueue(Protocol):
    def create(self, customer_id: str, reason: str) -> HandoffResponse: ...


class SimulatedOfferSender:
    """Pretends to deliver an offer; deterministic and without I/O."""

    def send(self, customer_id: str, product: str, channel: str) -> ConfirmResponse:
        return ConfirmResponse(
            status=SIMULATED_SENT,
            customer_id=customer_id,
            product=product,
            channel=channel,
            provider_message_id=f"demo-{customer_id}-{channel}".replace(" ", "-"),
        )


class SimulatedHandoffQueue:
    """Pretends to enqueue a human handoff; deterministic and without I/O."""

    def create(self, customer_id: str, reason: str) -> HandoffResponse:
        return HandoffResponse(
            status=HANDOFF_CREATED,
            customer_id=customer_id,
            reason=reason,
            queue=HANDOFF_QUEUE,
        )
