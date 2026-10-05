from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.chat.model import ChatModelError
from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import ChatService
from app.nba.schemas import ErrorResponse
from app.nba.service import CustomerNotFound

router = APIRouter(tags=["conversational-agent"])


def get_chat_service(request: Request) -> ChatService:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat agent is unavailable: no LLM provider is configured.",
        )
    return service


@router.post(
    "/agent/chat",
    response_model=ChatResponse,
    summary="Run one stateless chat turn with the customer-facing agent",
    description=(
        "Classifies the intent of the latest user message with an LLM, then application code "
        "decides and executes: CONFIRM sends the simulated offer only when the decision is "
        "ACTION, REQUEST_HUMAN creates a handoff, and every other intent executes nothing. "
        "The NBA engine is recomputed on every turn; the LLM sees only customer-safe facts. "
        "Send the full history on each request; nothing is stored."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Customer not found in the pre-test customer snapshot.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "The LLM provider failed before any action ran.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "No LLM provider is configured.",
        },
    },
)
def chat(
    body: Annotated[ChatRequest, Body()],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        return service.reply(body)
    except CustomerNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ChatModelError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
