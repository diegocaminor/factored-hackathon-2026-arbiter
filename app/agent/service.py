from __future__ import annotations

from typing import Any

from app.agent.schemas import AgentRecommendation, AgentRunResponse
from app.nba.loader import NBAArtifacts
from app.nba.service import CustomerNotFound, NBAService
from app.nba.values import optional_float, optional_int, optional_str
from propensity.langgraph_nba_agent import AgentContext, build_nba_graph


class AgentService:
    """Runs the vendored NBA workflow graph and maps its final state to the API contract."""

    def __init__(self, graph: Any, nba_service: NBAService) -> None:
        self._graph = graph
        self._nba = nba_service

    def run(self, customer_id: str, user_confirmed: bool) -> AgentRunResponse:
        if not self._nba.has_customer(customer_id):
            raise CustomerNotFound(customer_id)
        state = self._graph.invoke({"customer_id": customer_id, "user_confirmed": user_confirmed})
        return _to_response(state, customer_id, user_confirmed)


def build_agent_service(artifacts: NBAArtifacts, nba_service: NBAService) -> AgentService:
    """Build the agent context from loaded artifacts and compile the graph once."""
    context = AgentContext(
        model=artifacts.model,
        action_catalog=artifacts.action_catalog,
        customer_snapshot=artifacts.customer_snapshot,
        model_features=list(artifacts.model_features),
        categorical_features=list(artifacts.categorical_features),
        customer_id_col=artifacts.customer_id_column,
        min_historical_sends=artifacts.min_historical_sends,
    )
    return AgentService(build_nba_graph(context), nba_service)


def _to_response(state: dict[str, Any], customer_id: str, user_confirmed: bool) -> AgentRunResponse:
    # customer_row and ranked_actions are internal and deliberately not mapped.
    recommendation = state["recommendation"]
    return AgentRunResponse(
        customer_id=customer_id,
        user_confirmed=user_confirmed,
        status=state["status"],
        recommendation=AgentRecommendation(
            decision=recommendation["decision"],
            product=optional_str(recommendation["promoted_product"]),
            channel=optional_str(recommendation["send_channel"]),
            propensity=optional_float(recommendation["propensity_raw"]),
            expected_conversion_value=optional_float(recommendation["expected_conversion_value"]),
            estimated_send_cost=optional_float(recommendation["estimated_send_cost"]),
            expected_value=optional_float(recommendation["expected_value"]),
            historical_support=optional_int(recommendation["historical_support"]),
        ),
        consent_required=state.get("consent_required"),
        product_details=state.get("product_details") or None,
        execution_result=state.get("execution_result"),
        assistant_message=state["assistant_message"],
    )
