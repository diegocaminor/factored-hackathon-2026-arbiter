# Tasks

## 1. Simulated adapters and schemas

- [ ] 1.1 Add `app/execution/schemas.py` with `ConfirmResponse` (`status: Literal["SIMULATED_SENT"]`, `customer_id`, `product`, `channel`, `provider_message_id`), `HandoffRequest` (`reason: str | None = None`), and `HandoffResponse` (`status: Literal["HANDOFF_CREATED"]`, `customer_id`, `reason`, `queue`). Verify the JSON schemas render with `model_json_schema()`.
- [ ] 1.2 Add `app/execution/adapters.py` with the `OfferSender` and `HandoffQueue` protocols and the `SimulatedOfferSender` and `SimulatedHandoffQueue` adapters, using constants for the status values, the `sales-assistance` queue, and the default reason. Verify with unit tests that pin the literal values, including `provider_message_id == "demo-CLI-X-Push"`, space-to-hyphen replacement for a channel containing a space, and identical outputs on repeated calls.

## 2. Execution service

- [ ] 2.1 Add `NBAService.has_customer(customer_id)` backed by the existing customer index. Verify with unit tests for known and unknown IDs, and confirm the existing NBA tests still pass unchanged.
- [ ] 2.2 Add `app/execution/service.py` with `ExecutionService.confirm(customer_id)` and `ExecutionService.handoff(customer_id, reason)`, plus `RecommendationNotActionable(customer_id, decision)`. Verify with unit tests over `tests/nba/fakes` and spy adapters: `ACTION` sends the recommended product and channel; each of the three `NO_ACTION_*` decisions raises `RecommendationNotActionable` without sending; unknown customers raise `CustomerNotFound` for both operations without sending or creating; handoff uses the default reason for `None`, and uses a custom reason otherwise.

## 3. HTTP endpoints and wiring

- [ ] 3.1 Add `app/execution/router.py` with sync `POST /customers/{customer_id}/confirm` and `POST /customers/{customer_id}/handoff`, a `get_execution_service` dependency, an optional `Body(default=None)` for handoff, and documented 404 and 409 (`ErrorResponse`) responses. Build `ExecutionService` in the lifespan after `NBAService` and register the router in `app/main.py`. Verify with TestClient tests: confirm returns 200 for an `ACTION` customer with `product` and `channel` equal to GET next-best-action, 409 with the decision in `detail` for each NO_ACTION customer, and 404 for an unknown ID; handoff returns 200 for an `ACTION` and a NO_ACTION customer, 404 for an unknown ID, the default reason with no body, `{}`, or `{"reason": null}`, a custom reason when provided, and 422 for `{"reason": 123}` and for a non-object body; repeated confirms return identical bodies; OpenAPI lists both operations with their response schemas, the 404 and 409 responses, and an optional handoff body.
- [ ] 3.2 Extend `tests/nba/test_integration.py`, or add a sibling integration module with the same skip rule, to verify against real artifacts that the demo customer `CLI-P21780PQ8D9W` confirms with `SIMULATED_SENT`, Tarjeta Crédito, Push, and `demo-CLI-P21780PQ8D9W-Push`; that a consent-false customer gets 409 on confirm and 200 on handoff; and that no artifact is read after startup. Verify the full suite passes.
- [ ] 3.3 Update README with both endpoints: purpose, status codes, the optional handoff body, example `curl` requests with real responses, the note that execution is simulated and stateless (repeated confirms simulate repeated sends), and the absence of provider integrations. Verify every documented command runs as written against a running server.

## 4. Integration and scope checks

- [ ] 4.1 Run the Docker image with the artifacts mounted and exercise confirm (200, 409, 404) and handoff (200, custom reason, 404) on port 8000. Review the final diff: `src/propensity/` unchanged, no new dependencies, no LangGraph import reachable from `app/`, `next-best-action` responses unchanged, and no outbound network or provider code. Run the full test suite and `openspec validate add-confirm-handoff-flow --strict`.
