from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.agent.schemas import AgentRunRequest, AgentRunResponse
from app.agent.service import AgentService
from app.nba.schemas import ErrorResponse
from app.nba.service import CustomerNotFound

router = APIRouter(tags=["agent"])


def get_agent_service(request: Request) -> AgentService:
    return request.app.state.agent_service


@router.post(
    "/agent/run",
    response_model=AgentRunResponse,
    summary="Run the NBA workflow graph for a customer",
    description=(
        "Runs the LangGraph workflow once: load customer, recommend, then ACTION + "
        "user_confirmed=true executes the simulated offer (COMPLETED), ACTION + false creates "
        "a human handoff (HANDOFF), and NO_ACTION decisions end without execution. Stateless; "
        "no LLM is involved, and the NBA engine decides every recommendation value."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Customer not found in the pre-test customer snapshot.",
        }
    },
)
def run_agent(
    body: Annotated[AgentRunRequest, Body()],
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentRunResponse:
    try:
        return service.run(body.customer_id, body.user_confirmed)
    except CustomerNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
