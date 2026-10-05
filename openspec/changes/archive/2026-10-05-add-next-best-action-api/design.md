# Design

## Context

See `proposal.md` for motivation and `specs/` for the required behavior. Current state:

- `app/main.py` holds a single FastAPI instance with `GET /health`. There are no routers, settings, or tests.
- `src/propensity/` is vendored unchanged from Drive. `nba_engine.recommend_next_best_action(customer_row, action_catalog, model, model_features, categorical_features, min_historical_sends)` returns `(NBAResult, scored_actions_df)`. `NBAResult` already uses `expected_conversion_value` and `historical_support`. Product, channel, and propensity are named `promoted_product`, `send_channel`, and `propensity_raw`.
- Engine modules use absolute imports (`from propensity.x import ...`). `propensity/__init__.py` star-imports `modeling` and `evaluation`, so importing any submodule pulls in scikit-learn. `config.py` hardcodes a Colab Drive path but does no I/O at import time.
- Required artifacts under `ARTIFACTS_DIR`: `final_evaluation/catboost_20261004_222052/model.joblib` (pickled CatBoost model), `nba/action_catalog_pretest.parquet` (60 rows), `nba/customer_snapshot_pretest.parquet` (149,835 rows, 12 MB), and `nba/nba_metadata.json` (feature lists and `min_historical_sends`).

## Goals / Non-Goals

**Goals:** The HTTP layer is a thin adapter over the unmodified engine. Artifacts load once and fail fast. Recommendation logic can be tested without CatBoost or artifacts.

**Non-Goals:** No changes to `src/propensity`. No generic model registry, caching layer, async inference, or readiness endpoint. No hot-reload of artifacts.

## Decisions

1. **Feature package `app/nba/` (screaming structure).** It contains `settings.py` (artifact paths), `loader.py` (reads artifacts into an immutable bundle), `service.py` (`NBAService`: lookup, engine call, mapping), `schemas.py` (Pydantic models), and `router.py` (HTTP only). `app/main.py` keeps `/health`, registers the router, and owns the lifespan. *Alternative:* one `main.py`. Rejected because HTTP concerns, I/O, and mapping would mix in one file, and the service could not be tested without HTTP.

2. **Lifespan-loaded singleton exposed through a dependency.** The lifespan builds `NBAService` from the loaded bundle and stores it on `app.state`. `get_nba_service()` returns it. Tests replace it with `dependency_overrides`. *Alternatives:* module-level globals, which would load at import and break test isolation, or per-request loading, which violates the spec.

3. **Metadata is the single source of engine parameters.** `model_features`, `categorical_features`, and `min_historical_sends` come from `nba_metadata.json`, the record of what the frozen model was trained with. The loader fails if these keys are missing. *Alternative:* rebuild `NUMERIC + CATEGORICAL + INTERACTION` from `propensity.config`. Rejected because it duplicates the notebook's feature composition and could drift from the frozen model.

4. **O(1) customer lookup.** At load time, build a `dict[str, int]` that maps the stringified `customer_id` to its row position, then take the row with `snapshot.iloc[pos]`. The service resolves the ID column with the same candidate list the engine uses (`customer_id`, `client_id`, `user_id`). *Alternative:* reuse `langgraph_nba_agent.find_customer_row`. Rejected because it runs `astype(str)` over 150k rows on every call and would make LangGraph a runtime dependency.

5. **Thin mapping with explicit JSON sanitization.** The service converts `NBAResult` into the response schema (`promoted_product→product`, `send_channel→channel`, `propensity_raw→propensity`, `customer_id→str`) and adds `country` from the snapshot row. Candidates come from `scored_actions.head(5)`. Each numpy scalar is converted with `float()` or `int()`, and NaN or infinity becomes `None`. `decision` is a `Literal` of the four engine values. If the engine returns a value outside that set, the request fails with a 500 instead of passing an undocumented value to clients.

6. **Sync endpoint.** The route is a plain `def`, so FastAPI runs it in its threadpool. CatBoost `predict_proba` on fewer than 25 rows is fast, CPU-bound, and safe for concurrent reads. *Alternative:* `async def`. Rejected because it would block the event loop during inference.

7. **Import path through `PYTHONPATH=src`.** Local runs use `PYTHONPATH=src uvicorn app.main:app --reload`. The Dockerfile sets `ENV PYTHONPATH=/app/src`. *Alternatives:* a `pyproject.toml` editable install, which adds packaging for a vendored research package, or `sys.path` manipulation in `app/`, which is hidden coupling. Both rejected.

8. **Accept the package's transitive imports.** scikit-learn becomes a runtime dependency because `propensity/__init__.py` imports it. *Alternative:* trim `__init__.py`. Rejected because the change commits to not modifying `src/propensity`, and notebooks may depend on the star exports.

9. **Pins derived from the frozen model.** Pin catboost, scikit-learn, joblib, pandas, numpy, and pyarrow to versions that load `model.joblib` and reproduce the notebook's demo recommendation (`CLI-P21780PQ8D9W` → `ACTION`, Tarjeta Crédito, Push). Determine versions by loading the model before writing the pins. Base image stays `python:3.12-slim`.

10. **Artifacts mounted at run time, never baked in.** The image sets `ENV ARTIFACTS_DIR=/app/artifacts/propensity`. Users run with `-v "$PWD/artifacts/propensity:/app/artifacts/propensity:ro"`. The `.dockerignore` allowlist gains `src/propensity/**` (excluding caches), and `artifacts/` stays excluded. The image remains reproducible from git alone, and model files never enter image layers.

11. **Tests with pytest and TestClient.** Unit tests use a fake `NBAService`, or a real `NBAService` with a stub model and tiny in-memory frames, to cover 404, every decision, candidates, strict JSON, and OpenAPI. An integration test marked to skip when artifacts are absent compares the endpoint with a direct engine call for real customers. Test dependencies go in `requirements-dev.txt` so the runtime image stays lean.

## Risks / Trade-offs

- [Pickled model incompatible with the pinned catboost or sklearn] → Load the model and reproduce the demo customer first, and pin exactly what works. The error names the artifact.
- [Memory: the snapshot DataFrame plus the model use roughly 150–300 MB per process] → Acceptable for a single Uvicorn worker. Document it, and avoid multiple workers until needed.
- [Image size grows by several hundred MB from catboost, sklearn, and pyarrow] → Accepted for the hackathon. A multi-stage or slim build is deferred.
- [Slower startup of a few seconds to read parquet and unpickle] → Fail-fast happens during startup, so a slow start is visible and never serves partial state.
- [`config.py` still points at Drive] → The app never reads `config.ARTIFACT_DIR`. Settings are the only path source.
- [Raw propensity is misread as a calibrated probability] → Schema field descriptions say "raw, uncalibrated model score".
- [Plain `docker run` without the mount now fails] → This is the intended fail-fast behavior. README shows the mount command and the expected startup error.

## Migration Plan

1. Populate `artifacts/propensity/` from Drive (manual, one time).
2. Ship code, pins, Docker, and README changes together. Existing `/health` and `/docs` behavior stays the same.
3. Rollback means reverting the change's commits. The vendored package commit `32293b3` can stay, because it has no runtime effect without this change.
