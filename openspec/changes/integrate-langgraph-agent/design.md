# Design

## Context

See `proposal.md` for motivation and `specs/agent-orchestration/spec.md` for behavior. Facts verified in an exploration spike (throwaway container, real artifacts, `langgraph==1.2.12` on the current pins, `pip check` clean):

- `build_nba_graph(ctx)` compiles in about 2 ms. One `invoke` takes 14–38 ms. The graph has no checkpointer and no interrupts, and `user_confirmed` is read from the initial state. If the flag is missing the graph routes to handoff. An unknown `customer_id` raises `KeyError` from `find_customer_row`.
- The final state holds `customer_row` (a `pd.Series`), `recommendation` (`NBAResult.__dict__`, with the engine's field names), `ranked_actions` (10 rows with 20 internal catalog columns), `product_details`, `consent_required`, `execution_result`, `assistant_message`, and `status` (`COMPLETED`, `HANDOFF`, or the `NO_ACTION_*` decision).
- The graph has no LLM. `assistant_message` is built from engine values with f-strings.
- `get_next_best_action_tool` hardcodes `min_historical_sends=100` (`src/propensity/langgraph_nba_agent.py:86`), while the API reads the value from `nba_metadata.json` through `NBAArtifacts`.
- The app already loads `NBAArtifacts` once and exposes `NBAService.has_customer()`. The execution payloads match the graph's tools because their values are pinned.

## Goals / Non-Goals

**Goals:** Reuse `AgentContext` and `build_nba_graph()` unchanged, apart from the threshold field. Keep one threshold value end to end. Keep a thin adapter from graph state to the API contract. Prove fidelity with the existing endpoints in tests.

**Non-Goals:** No graph reimplementation, LLM, streaming, checkpointer, `thread_id`, or resumable flow. No refactor of the graph's own simulated tools.

## Decisions

1. **Feature package `app/agent/`.** It contains `schemas.py`, `service.py` (`AgentService` plus a `build_agent_service(artifacts, nba_service)` factory), and `router.py`. This follows the `app/nba/` and `app/execution/` pattern. Only this package imports LangGraph-related modules.

2. **Minimal vendored edit for the threshold.** `AgentContext` gains `min_historical_sends: int`, required and appended after the existing fields, with no default. `get_next_best_action_tool` passes `ctx.min_historical_sends`. Nothing else in `langgraph_nba_agent.py` changes. *Alternatives:* monkeypatch the tool from `app/` (hidden coupling); a startup guard comparing metadata with 100 (still two copies of the value). Both rejected by the user.

3. **Threshold validation in the loader.** `load_artifacts` rejects a `min_historical_sends` that is not an `int`, is a `bool`, or is `<= 0`, with an `ArtifactLoadError` naming the metadata path and the key. The value then flows `NBAArtifacts → AgentContext` and `NBAArtifacts → NBAService`, read from a single field.

4. **Build once in the lifespan.** After `NBAService` and `ExecutionService`, the lifespan calls `build_agent_service(artifacts, nba_service)`. That builds `AgentContext(model, action_catalog, customer_snapshot, list(model_features), list(categorical_features), customer_id_column, min_historical_sends)`, compiles the graph, and stores `AgentService` on `app.state`. No artifact is read again.

5. **404 before invocation.** `AgentService.run` checks `nba_service.has_customer()` and raises `CustomerNotFound` before calling `graph.invoke`, so the graph's `KeyError` cannot surface as a 500 for unknown IDs.

6. **Strict request schema.** `AgentRunRequest(customer_id: str, user_confirmed: StrictBool)` is a required body. `StrictBool` rejects `"true"` and `1`, so a malformed flag can never fall through to the graph's implicit-false handoff.

7. **Explicit response mapping.** `AgentRunResponse` contains `customer_id`, `user_confirmed`, `status` (a `Literal` of `COMPLETED`, `HANDOFF`, and the three `NO_ACTION_*` values), `recommendation` (`AgentRecommendation`, using the NBA API field names: `promoted_product→product`, `send_channel→channel`, `propensity_raw→propensity`), `consent_required: bool | None`, `product_details: ProductDetails | None`, `execution_result: ConfirmResponse | HandoffResponse | None` (reusing the execution schemas and discriminated by `status`), and `assistant_message`. `customer_row` and `ranked_actions` are dropped. An unexpected status or payload fails validation and returns 500 instead of an undocumented contract.

8. **Shared value sanitizers.** The private `_optional_float`, `_optional_int`, and `_optional_str` helpers move from `app/nba/service.py` to `app/nba/values.py` as public functions. They convert NaN and infinity to `null` for the agent's recommendation mapping too. NBA behavior is unchanged.

9. **Sync endpoint.** `POST /agent/run` is a plain `def`, so it runs in FastAPI's threadpool. A compiled graph without a checkpointer is safe for concurrent independent invocations.

10. **Tests use the real graph.** `build_nba_graph` runs over the existing `tests/nba/fakes` artifacts (stub model), so tests exercise the actual orchestration without CatBoost. Fidelity tests compare `/agent/run` with `GET next-best-action`, `POST confirm`, and `POST handoff` in the same app. A threshold test raises `min_historical_sends` above the fake Chile catalog's sends and checks that both the agent and the NBA endpoint return `NO_ACTION_NO_SUPPORTED_CANDIDATES`. Integration tests repeat the fidelity checks on real artifacts.

## Risks / Trade-offs

- [The vendored module now diverges from the Drive copy] → The edit is a single field, documented in the proposal and README. Notebook 09 must pass the new argument when it runs against the repo.
- [The graph's simulated tools still live inside the graph] → Parity tests pin agent `execution_result` equal to the confirm and handoff endpoints. Unifying them is a later change.
- [`find_customer_row` scans 150k rows twice per run] → Measured end to end at 14–38 ms, which is acceptable. Optimizing it would mean editing more of the vendored graph.
- [LangGraph increases image size and import time] → Accepted. The version is pinned and already checked.
- [The status vocabulary is coupled to graph internals] → A `Literal` plus validation makes any graph change fail loudly in tests.

## Migration Plan

Additive endpoint plus one vendored field. Install `langgraph==1.2.12`, rebuild the image, and keep the same run command with mounted artifacts. Rollback means reverting the change's commits; nothing persistent is involved.
