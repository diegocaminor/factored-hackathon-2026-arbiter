# Proposal

## Why

The NBA workflow (load customer, recommend, route ACTION versus NO_ACTION, confirmation gate, simulated execution, human handoff) exists as a LangGraph graph in `src/propensity/langgraph_nba_agent.py`, but it only runs from notebook 09. Exposing it through FastAPI gives the demo one call that runs the whole orchestrated workflow. The graph contains no LLM: the CatBoost model and the NBA engine stay the only source of product, channel, propensity, and expected value.

## What Changes

- Add `POST /agent/run` with a JSON body `{customer_id: string, user_confirmed: bool}`, where both fields are required. It invokes the existing compiled graph once and returns a mapped result:
  - `ACTION` with `user_confirmed=true` executes the simulated offer (`status` `COMPLETED`).
  - `ACTION` with `user_confirmed=false` creates a human handoff (`status` `HANDOFF`).
  - Any `NO_ACTION_*` decision ends without execution (`status` equals the decision).
- Return 404 before invoking the graph for unknown customers, and 422 when `user_confirmed` is missing or not a boolean.
- The response schema reuses the NBA API field names for the recommendation and exposes the graph's `status`, `consent_required`, `product_details`, `execution_result`, and `assistant_message`. It never exposes `customer_row` or internal catalog columns.
- Build `AgentContext` from the artifacts already loaded at startup and compile `build_nba_graph()` once in the lifespan. Do not reimplement any graph node.
- **Make `min_historical_sends` a single source of truth.** Add a required `min_historical_sends: int` field (no default) to `AgentContext` and use it in `get_next_best_action_tool` in place of the hardcoded `100` (`src/propensity/langgraph_nba_agent.py:86`). The value comes from `nba_metadata.json`, which the loader now validates as a positive integer. This is the first intentional edit to the vendored `src/propensity` package.
- Add `langgraph==1.2.12`, already checked against the current pins.
- **Compatibility:** notebook 09 constructs `AgentContext` without `min_historical_sends`. If it is rerun against this repository version, it must pass `min_historical_sends=metadata["min_historical_sends"]`. The notebook itself is not modified.

Out of scope: any LLM, a resumable `WAITING_CONFIRMATION` flow (checkpointer, `thread_id`, persisted graph state), persistence, UI, and changes to the NBA, confirm, or handoff endpoints. The confirmation preview remains `GET /customers/{customer_id}/next-best-action`.

## Capabilities

### New Capabilities

- `agent-orchestration`: Running the NBA workflow graph over HTTP as a stateless single request, including routing outcomes, the confirmation gate, not-found and validation behavior, the response contract, and fidelity to the NBA engine and the execution endpoints.

### Modified Capabilities

None. `http-service`, `next-best-action`, and `offer-execution` requirements are unchanged. Only README examples change.

## Impact

- Code: a new `app/agent/` feature package (schemas, service, router), lifespan wiring in `app/main.py`, stricter metadata validation in `app/nba/loader.py`, and a minimal edit to `src/propensity/langgraph_nba_agent.py` (one required context field; the tool reads it).
- Dependencies: `langgraph==1.2.12` in `requirements.txt`, so the Docker image grows.
- APIs: one new endpoint; existing endpoints are unchanged.
- Docs: README gains `/agent/run` examples and the notebook 09 compatibility note.
- Tests: unit, router, and fidelity tests, including integration tests on real artifacts.
