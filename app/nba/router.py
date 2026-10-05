from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from app.nba.schemas import ErrorResponse, NextBestActionResponse
from app.nba.service import CustomerNotFound, NBAService

router = APIRouter(tags=["next-best-action"])


def get_nba_service(request: Request) -> NBAService:
    return request.app.state.nba_service


@router.get(
    "/customers/{customer_id}/next-best-action",
    response_model=NextBestActionResponse,
    summary="Get the next best action for a customer",
    description=(
        "Runs the frozen NBA engine for a customer in the pre-test snapshot. "
        "Every decision for a known customer, including NO_ACTION reasons, returns HTTP 200."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Customer not found in the pre-test customer snapshot.",
        }
    },
)
def get_next_best_action(
    customer_id: Annotated[str, Path(description="Customer identifier, e.g. CLI-P21780PQ8D9W.")],
    service: Annotated[NBAService, Depends(get_nba_service)],
    include_candidates: Annotated[
        bool, Query(description="Include up to five top-ranked scored actions.")
    ] = False,
) -> NextBestActionResponse:
    try:
        return service.recommend(customer_id, include_candidates=include_candidates)
    except CustomerNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
