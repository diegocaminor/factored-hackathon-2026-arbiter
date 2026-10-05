# Design

## Context

See `proposal.md` for motivation and `specs/offer-execution/spec.md` for behavior. Current state:

- `app/nba/` serves recommendations: `NBAService.recommend(customer_id, include_candidates)` returns `NextBestActionResponse` or raises `CustomerNotFound`. `app/main.py` builds `NBAService` in the lifespan and stores it on `app.state`. Routers resolve services through `Depends`, and tests replace them with `dependency_overrides`.
- `src/propensity/langgraph_nba_agent.py` defines `simulate_offer_tool` (`SIMULATED_SENT`, `provider_message_id = f"demo-{customer_id}-{channel}".replace(" ", "-")`) and `handoff_to_human_tool` (`HANDOFF_CREATED`, queue `sales-assistance`). Its default handoff reason is "Customer did not confirm automated execution.". The module imports `langgraph` at the top, and LangGraph is not a runtime dependency.
- Test fakes in `tests/nba/fakes.py` provide a stub model and in-memory artifacts covering every decision value.

## Goals / Non-Goals

**Goals:** Execution is a separate feature that depends on the recommendation feature, never the reverse. Provider integration can be swapped in later without touching endpoints or the service. Payloads are byte-compatible with the agent's tools.

**Non-Goals:** No provider abstraction beyond what the two simulated actions need. No background jobs, retries, or event publishing. No change to `next-best-action` responses.

## Decisions

1. **Feature package `app/execution/`.** It contains `schemas.py` (request and response models), `adapters.py` (ports and simulated adapters), `service.py` (`ExecutionService`), and `router.py` (HTTP only). Acting on the world is a different capability from scoring, so it gets its own folder, matching the `app/nba/` structure. *Alternative:* add the endpoints to `app/nba/router.py`. Rejected because it mixes read-only scoring with side-effecting actions, and that file would grow with every future provider.

2. **Ports with simulated adapters.** `OfferSender.send(customer_id, product, channel) -> OfferDelivery` and `HandoffQueue.create(customer_id, reason) -> Handoff` are `typing.Protocol`s. `SimulatedOfferSender` and `SimulatedHandoffQueue` are pure and deterministic. `ExecutionService` receives them through its constructor. *Alternative:* inline the simulation in the service. Rejected because the first real provider would then rewrite the service and its tests instead of adding an adapter.

3. **Reimplement the agent's tool semantics instead of importing them.** The adapters reproduce the exact statuses, ID format, queue, and default reason as module constants. Tests pin those literal values. *Alternative:* import from `langgraph_nba_agent`, which needs LangGraph. *Alternative:* move the tools into a LangGraph-free module in `src/propensity`, which edits the vendored package. Both rejected. The duplication is a few lines, and the pinned constants catch drift.

4. **`confirm` recomputes through `NBAService.recommend()`.** The service calls `recommend(customer_id)`, lets `CustomerNotFound` propagate (404), raises `RecommendationNotActionable(customer_id, decision)` when `decision != "ACTION"` (409), and otherwise sends `product` and `channel` from that recommendation. No request body is read: with a deterministic engine and a frozen snapshot, the server's recommendation equals what the client saw. *Alternative:* the client echoes product and channel for cross-checking. Deferred until data can change between GET and POST.

5. **`handoff` checks existence without inference.** Add `NBAService.has_customer(customer_id) -> bool`, which reads the existing `customer_positions` index. `handoff` raises `CustomerNotFound` when it returns false. *Alternative:* call `recommend()` just to validate, which would run the model for an action that ignores the result. Rejected. This is the only edit to `app/nba/`; it adds a query and changes no behavior.

6. **Optional handoff body.** `HandoffRequest(reason: str | None = None)` is accepted as `Body(default=None)`, so no body, `{}`, and `{"reason": null}` all resolve to the default reason. FastAPI's validation returns 422 for non-object bodies or a non-string `reason`. Any body sent to `confirm` is ignored, because the route declares none.

7. **Wiring.** The lifespan builds `ExecutionService(nba_service, SimulatedOfferSender(), SimulatedHandoffQueue())` right after `NBAService` and stores it on `app.state`. `get_execution_service` exposes it, and tests override it or wire real services over the in-memory fakes. Endpoints are sync `def`, like the NBA route, because `confirm` runs inference.

8. **Contracts and errors.** Response models use `Literal` statuses (`SIMULATED_SENT` and `HANDOFF_CREATED`). Error responses reuse `ErrorResponse` from `app.nba.schemas` for the documented 404 and 409. Routers map `CustomerNotFound` to 404 and `RecommendationNotActionable` to 409, with a `detail` message that includes the decision.

9. **Tests.** Service tests use spy adapters to assert that nothing is sent or created on 404 or 409. Router tests check status codes, bodies, 422 handling, and OpenAPI. Both build real `NBAService` and `ExecutionService` instances on `tests/nba/fakes`. The existing integration module gains confirm and handoff checks against real artifacts: the demo customer is `ACTION`, and the first consent-false customer gets 409 on confirm and 200 on handoff.

## Risks / Trade-offs

- [Agent and API payloads drift] → Pinned constants and literal-value tests. A later LangGraph change should make the agent call these adapters instead of its own tools.
- [Repeated confirms simulate repeated sends] → Accepted for this change. Idempotency and audit are explicitly out of scope and documented in README.
- [`confirm` costs one inference per call] → Same cost as `GET next-best-action`, under 25 candidate rows.
- [Handoff is allowed for customers without marketing consent] → Intentional. A human advisor is the right path for them, and handoff sends nothing to the customer.
- [`ErrorResponse` imported across features] → Acceptable coupling for one shared schema. Move it to a shared module if a third feature needs it.

## Migration Plan

Additive only: two new routes, one new package, and one new read-only `NBAService` method. No configuration, artifact, or dependency changes. Rollback means reverting the change's commits.
