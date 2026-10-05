from __future__ import annotations

from app.execution.adapters import DEFAULT_HANDOFF_REASON, HandoffQueue, OfferSender
from app.execution.schemas import ConfirmResponse, HandoffResponse
from app.nba.service import CustomerNotFound, NBAService


class RecommendationNotActionable(Exception):
    def __init__(self, customer_id: str, decision: str) -> None:
        super().__init__(
            f"Customer {customer_id} has no actionable recommendation (decision: {decision})"
        )
        self.customer_id = customer_id
        self.decision = decision


class ExecutionService:
    """Acts on next best action recommendations through execution ports."""

    def __init__(
        self, nba_service: NBAService, offer_sender: OfferSender, handoff_queue: HandoffQueue
    ) -> None:
        self._nba = nba_service
        self._offer_sender = offer_sender
        self._handoff_queue = handoff_queue

    def confirm(self, customer_id: str) -> ConfirmResponse:
        recommendation = self._nba.recommend(customer_id)
        if (
            recommendation.decision != "ACTION"
            or recommendation.product is None
            or recommendation.channel is None
        ):
            raise RecommendationNotActionable(customer_id, recommendation.decision)
        return self._offer_sender.send(
            customer_id, recommendation.product, recommendation.channel
        )

    def handoff(self, customer_id: str, reason: str | None = None) -> HandoffResponse:
        if not self._nba.has_customer(customer_id):
            raise CustomerNotFound(customer_id)
        return self._handoff_queue.create(
            customer_id, DEFAULT_HANDOFF_REASON if reason is None else reason
        )
