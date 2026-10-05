from __future__ import annotations

from app.chat.guard import fallback_reply, guard_reply
from app.chat.model import ChatModel, ChatModelError
from app.chat.safe_view import build_safe_view, safe_outcome
from app.chat.schemas import ActionTaken, ChatRequest, ChatResponse, Intent
from app.execution.schemas import ConfirmResponse, HandoffResponse
from app.execution.service import ExecutionService
from app.nba.schemas import NextBestActionResponse
from app.nba.service import CustomerNotFound, NBAService

CHAT_HANDOFF_REASON = "Customer requested human assistance via chat."


class ChatService:
    """Runs one stateless chat turn: the model interprets, this code decides and executes."""

    def __init__(
        self, nba_service: NBAService, execution_service: ExecutionService, model: ChatModel
    ) -> None:
        self._nba = nba_service
        self._execution = execution_service
        self._model = model

    def reply(self, request: ChatRequest) -> ChatResponse:
        customer_id = request.customer_id
        if not self._nba.has_customer(customer_id):
            raise CustomerNotFound(customer_id)

        # The engine is recomputed every turn; nothing in the history is trusted.
        recommendation = self._nba.recommend(customer_id)
        view = build_safe_view(recommendation)
        classification = self._model.classify(request.messages, view)
        intent = classification.intent

        action_taken, result = self._dispatch(intent, recommendation)
        if result is not None:
            view = view.model_copy(update={"outcome": safe_outcome(result)})

        try:
            reply = guard_reply(
                self._model.write_reply(request.messages, view, intent, classification.language)
            )
        except ChatModelError:
            if view.outcome is None:
                raise
            reply = fallback_reply(view.outcome)

        return ChatResponse(
            customer_id=customer_id,
            reply=reply,
            intent=intent,
            action_taken=action_taken,
            execution_result=result,
        )

    def _dispatch(
        self, intent: Intent, recommendation: NextBestActionResponse
    ) -> tuple[ActionTaken, ConfirmResponse | HandoffResponse | None]:
        customer_id = recommendation.customer_id
        if intent is Intent.CONFIRM and recommendation.decision == "ACTION":
            return ActionTaken.OFFER_CONFIRMED, self._execution.confirm(customer_id)
        if intent is Intent.REQUEST_HUMAN:
            return ActionTaken.HANDOFF_CREATED, self._execution.handoff(
                customer_id, CHAT_HANDOFF_REASON
            )
        return ActionTaken.NONE, None
