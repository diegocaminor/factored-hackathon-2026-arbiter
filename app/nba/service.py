from __future__ import annotations

import pandas as pd

from app.nba.loader import NBAArtifacts
from app.nba.schemas import CandidateAction, NextBestActionResponse
from app.nba.values import optional_float, optional_int, optional_str
from propensity.nba_engine import recommend_next_best_action

CANDIDATE_LIMIT = 5


class CustomerNotFound(LookupError):
    def __init__(self, customer_id: str) -> None:
        super().__init__(f"Customer not found: {customer_id}")
        self.customer_id = customer_id


class NBAService:
    """Adapts the frozen NBA engine to the HTTP response contract."""

    def __init__(self, artifacts: NBAArtifacts) -> None:
        self._artifacts = artifacts

    def has_customer(self, customer_id: str) -> bool:
        return customer_id in self._artifacts.customer_positions

    def recommend(self, customer_id: str, include_candidates: bool = False) -> NextBestActionResponse:
        artifacts = self._artifacts
        position = artifacts.customer_positions.get(customer_id)
        if position is None:
            raise CustomerNotFound(customer_id)

        customer_row = artifacts.customer_snapshot.iloc[position]
        result, scored = recommend_next_best_action(
            customer_row=customer_row,
            action_catalog=artifacts.action_catalog,
            model=artifacts.model,
            model_features=list(artifacts.model_features),
            categorical_features=list(artifacts.categorical_features),
            min_historical_sends=artifacts.min_historical_sends,
        )

        return NextBestActionResponse(
            customer_id=customer_id,
            country=optional_str(customer_row.get("country")),
            decision=result.decision,
            product=optional_str(result.promoted_product),
            channel=optional_str(result.send_channel),
            propensity=optional_float(result.propensity_raw),
            expected_conversion_value=optional_float(result.expected_conversion_value),
            estimated_send_cost=optional_float(result.estimated_send_cost),
            expected_value=optional_float(result.expected_value),
            historical_support=optional_int(result.historical_support),
            candidates=_top_candidates(scored) if include_candidates else None,
        )


def _top_candidates(scored: pd.DataFrame) -> list[CandidateAction]:
    if scored.empty:
        return []
    top = scored.sort_values("rank").head(CANDIDATE_LIMIT)
    return [
        CandidateAction(
            rank=int(row["rank"]),
            product=str(row["promoted_product"]),
            channel=str(row["send_channel"]),
            propensity=optional_float(row["propensity_raw"]),
            expected_conversion_value=optional_float(row["estimated_conversion_value"]),
            estimated_send_cost=optional_float(row["estimated_send_cost"]),
            expected_value=optional_float(row["expected_value"]),
            historical_support=optional_int(row["historical_sends"]),
        )
        for _, row in top.iterrows()
    ]
