# Proposal

## Why

The deterministic Next Best Action (NBA) engine and its frozen CatBoost model can only be run from Colab notebooks today. The HTTP service from `bootstrap-fastapi-app` gives us a runnable boundary, so the next step is to expose the existing engine through that service. The model must not be retrained, re-tuned, or evaluated on the final test set.

## What Changes

- Add `GET /customers/{customer_id}/next-best-action`. It returns the engine's recommendation for a known customer: decision, product, channel, raw propensity, expected conversion value, estimated send cost, expected value, historical support, and the customer's country, so values in different currencies are never compared. Top-5 ranked candidate actions are included only when `include_candidates=true`.
- Return HTTP 404 for unknown customer IDs and HTTP 200 for every known customer, including all `NO_ACTION_*` decisions.
- Add an NBA application service. It loads the model, action catalog, customer snapshot, and NBA metadata once at startup, then calls the existing `recommend_next_best_action()` for each request. No ML logic is duplicated or modified.
- Resolve artifacts from an `ARTIFACTS_DIR` environment variable, defaulting to `./artifacts/propensity`. Startup fails fast if a required artifact is missing or cannot be loaded.
- Add Pydantic response schemas with JSON-safe types, and document the endpoint, its parameters, and its 404 response in Swagger.
- Add the runtime ML dependencies (pandas, numpy, pyarrow, catboost, scikit-learn, joblib) and make `src/propensity` importable both locally and in Docker.
- Package `src/propensity` into the image. Mount artifacts at run time instead of baking them in.
- **BREAKING**: the service no longer starts without the propensity package and NBA artifacts. Docker runs must mount the artifacts directory.

Already done before this change (commit `32293b3`): `src/propensity/` was copied from Google Drive and is versioned, and `artifacts/` is git-ignored. Artifacts are populated by hand from Drive. Drive is not a runtime dependency.

Out of scope: retraining, calibration (propensity stays raw and uncalibrated), loading final-test artifacts, the LangGraph agent, batch scoring, authentication, and a readiness endpoint.

## Capabilities

### New Capabilities

- `next-best-action`: Per-customer recommendations served over HTTP from the frozen NBA engine, including not-found handling, the decision vocabulary, economic fields, and optional ranked candidates.

### Modified Capabilities

- `http-service`: *Independent runtime* is replaced by a requirement that the service loads propensity code and NBA artifacts from a configurable directory and fails fast without them. *Local development execution* and *Container execution* change to cover the source path and the mounted artifacts.

## Impact

- Code: new `app/` modules (settings, NBA service, schemas, router) and a lifespan wired into `app/main.py`. `src/propensity` stays unchanged.
- Dependencies: `requirements.txt` gains the ML runtime stack, pinned to versions that can unpickle `model.joblib`. A test dependency is added.
- Container: `Dockerfile` and `.dockerignore` change to include `src/propensity`. The image grows because of the ML dependencies. `docker run` needs `-v .../artifacts/propensity:...`.
- Docs: README gains artifact setup, `ARTIFACTS_DIR`, the new endpoint, and the updated run commands.
- Data: reads only pre-test artifacts (`action_catalog_pretest`, `customer_snapshot_pretest`), the frozen model, and `nba_metadata.json`.
