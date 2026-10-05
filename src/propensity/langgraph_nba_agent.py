
from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, Literal, Any

import pandas as pd
from langgraph.graph import StateGraph, END

from propensity.nba_engine import recommend_next_best_action


class AgentState(TypedDict, total=False):
    customer_id: str
    user_message: str
    customer_row: Any
    recommendation: dict
    ranked_actions: list[dict]
    product_details: dict
    consent_required: bool
    user_confirmed: bool
    execution_result: dict
    assistant_message: str
    status: str


PRODUCT_DETAILS = {
    "Cuenta Ahorro": {
        "name": "Cuenta Ahorro",
        "summary": "Cuenta para ahorrar y gestionar fondos de uso cotidiano.",
    },
    "Cuenta Corriente": {
        "name": "Cuenta Corriente",
        "summary": "Cuenta transaccional para pagos, transferencias y manejo frecuente de dinero.",
    },
    "Inversión": {
        "name": "Inversión",
        "summary": "Producto orientado a colocar fondos con un objetivo de rentabilidad.",
    },
    "Préstamo Hipotecario": {
        "name": "Préstamo Hipotecario",
        "summary": "Financiamiento de largo plazo para compra o mejora de vivienda.",
    },
    "Préstamo Personal": {
        "name": "Préstamo Personal",
        "summary": "Crédito de libre disponibilidad para necesidades personales.",
    },
    "Seguro": {
        "name": "Seguro",
        "summary": "Producto de protección financiera frente a eventos cubiertos.",
    },
    "Tarjeta Crédito": {
        "name": "Tarjeta Crédito",
        "summary": "Línea de crédito revolvente para compras y pagos.",
    },
}


@dataclass
class AgentContext:
    model: Any
    action_catalog: pd.DataFrame
    customer_snapshot: pd.DataFrame
    model_features: list[str]
    categorical_features: list[str]
    customer_id_col: str


def find_customer_row(ctx: AgentContext, customer_id: str) -> pd.Series:
    match = ctx.customer_snapshot[
        ctx.customer_snapshot[ctx.customer_id_col].astype(str) == str(customer_id)
    ]
    if match.empty:
        raise KeyError(f"Customer not found: {customer_id}")
    return match.iloc[0]


def get_next_best_action_tool(ctx: AgentContext, customer_id: str) -> tuple[dict, pd.DataFrame]:
    row = find_customer_row(ctx, customer_id)
    rec, scored = recommend_next_best_action(
        customer_row=row,
        action_catalog=ctx.action_catalog,
        model=ctx.model,
        model_features=ctx.model_features,
        categorical_features=ctx.categorical_features,
        min_historical_sends=100,
    )
    return rec.__dict__, scored


def get_product_details_tool(product: str | None) -> dict:
    if not product:
        return {}
    return PRODUCT_DETAILS.get(
        product,
        {"name": product, "summary": "No additional product description configured."},
    )


def simulate_offer_tool(customer_id: str, product: str, channel: str) -> dict:
    return {
        "status": "SIMULATED_SENT",
        "customer_id": customer_id,
        "product": product,
        "channel": channel,
        "provider_message_id": f"demo-{customer_id}-{channel}".replace(" ", "-"),
    }


def handoff_to_human_tool(customer_id: str, reason: str) -> dict:
    return {
        "status": "HANDOFF_CREATED",
        "customer_id": customer_id,
        "reason": reason,
        "queue": "sales-assistance",
    }


def build_nba_graph(ctx: AgentContext):
    graph = StateGraph(AgentState)

    def load_customer(state: AgentState):
        row = find_customer_row(ctx, state["customer_id"])
        return {"customer_row": row, "status": "CUSTOMER_LOADED"}

    def recommend(state: AgentState):
        rec, scored = get_next_best_action_tool(ctx, state["customer_id"])
        return {
            "recommendation": rec,
            "ranked_actions": scored.head(10).to_dict(orient="records") if not scored.empty else [],
            "status": "NBA_READY",
        }

    def route_after_recommendation(state: AgentState) -> Literal["prepare_offer", "no_action"]:
        decision = state["recommendation"]["decision"]
        return "prepare_offer" if decision == "ACTION" else "no_action"

    def prepare_offer(state: AgentState):
        rec = state["recommendation"]
        details = get_product_details_tool(rec["promoted_product"])
        msg = (
            f"Recommended next best action: offer {rec['promoted_product']} via "
            f"{rec['send_channel']}. Estimated propensity: {rec['propensity_raw']:.4%}. "
            f"Expected value: {rec['expected_value']:.2f} in the customer's local currency. "
            f"{details.get('summary', '')} Confirmation is required before execution."
        )
        return {
            "product_details": details,
            "consent_required": True,
            "assistant_message": msg,
            "status": "WAITING_CONFIRMATION",
        }

    def no_action(state: AgentState):
        rec = state["recommendation"]
        return {
            "assistant_message": f"No outbound action recommended. Decision: {rec['decision']}.",
            "status": rec["decision"],
        }

    def confirmation_router(state: AgentState) -> Literal["execute_offer", "handoff"]:
        return "execute_offer" if bool(state.get("user_confirmed")) else "handoff"

    def execute_offer(state: AgentState):
        rec = state["recommendation"]
        result = simulate_offer_tool(
            state["customer_id"],
            rec["promoted_product"],
            rec["send_channel"],
        )
        return {
            "execution_result": result,
            "assistant_message": (
                f"Offer simulated successfully for {rec['promoted_product']} "
                f"via {rec['send_channel']}."
            ),
            "status": "COMPLETED",
        }

    def handoff(state: AgentState):
        result = handoff_to_human_tool(
            state["customer_id"],
            "Customer did not confirm automated execution.",
        )
        return {
            "execution_result": result,
            "assistant_message": "No automated send performed. A human handoff was created.",
            "status": "HANDOFF",
        }

    graph.add_node("load_customer", load_customer)
    graph.add_node("recommend", recommend)
    graph.add_node("prepare_offer", prepare_offer)
    graph.add_node("no_action", no_action)
    graph.add_node("execute_offer", execute_offer)
    graph.add_node("handoff", handoff)

    graph.set_entry_point("load_customer")
    graph.add_edge("load_customer", "recommend")
    graph.add_conditional_edges(
        "recommend",
        route_after_recommendation,
        {
            "prepare_offer": "prepare_offer",
            "no_action": "no_action",
        },
    )
    graph.add_edge("no_action", END)
    graph.add_conditional_edges(
        "prepare_offer",
        confirmation_router,
        {
            "execute_offer": "execute_offer",
            "handoff": "handoff",
        },
    )
    graph.add_edge("execute_offer", END)
    graph.add_edge("handoff", END)

    return graph.compile()
