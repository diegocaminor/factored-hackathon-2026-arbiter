from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request, status

from app.execution.schemas import ConfirmResponse, HandoffRequest, HandoffResponse
from app.execution.service import ExecutionService, RecommendationNotActionable
from app.nba.schemas import ErrorResponse
from app.nba.service import CustomerNotFound

router = APIRouter(tags=["offer-execution"])

CustomerId = Annotated[str, Path(description="Customer identifier, e.g. CLI-P21780PQ8D9W.")]
NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Customer not found in the pre-test customer snapshot.",
    }
}


def get_execution_service(request: Request) -> ExecutionService:
    return request.app.state.execution_service


@router.post(
    "/customers/{customer_id}/confirm",
    response_model=ConfirmResponse,
    summary="Confirm and simulate sending the recommended offer",
    description=(
        "Recomputes the customer's next best action and, when the decision is ACTION, "
        "simulates sending that offer. No provider is contacted and nothing is persisted; "
        "repeated calls simulate repeated sends."
    ),
    responses={
        **NOT_FOUND_RESPONSE,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The customer's current decision is not ACTION.",
        },
    },
)
def confirm(
    customer_id: CustomerId,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> ConfirmResponse:
    try:
        return service.confirm(customer_id)
    except CustomerNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RecommendationNotActionable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/customers/{customer_id}/handoff",
    response_model=HandoffResponse,
    summary="Create a simulated human handoff",
    description=(
        "Escalates a known customer to the human sales-assistance queue, whatever the "
        "current decision. No external system is contacted and nothing is persisted."
    ),
    responses=NOT_FOUND_RESPONSE,
)
def handoff(
    customer_id: CustomerId,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    body: Annotated[HandoffRequest | None, Body()] = None,
) -> HandoffResponse:
    try:
        return service.handoff(customer_id, body.reason if body else None)
    except CustomerNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
