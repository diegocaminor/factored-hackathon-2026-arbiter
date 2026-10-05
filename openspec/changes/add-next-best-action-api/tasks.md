# Tasks

## 1. Artifacts and runtime dependencies

- [ ] 1.1 Confirm the four required artifacts exist under `./artifacts/propensity` at the paths listed in design.md (model, action catalog, customer snapshot, metadata) and that no final-test artifact is present in that tree; verify with a file listing and `git check-ignore` showing they are untracked.
- [ ] 1.2 In a clean Python 3.12 venv, find catboost, scikit-learn, joblib, pandas, numpy, and pyarrow versions that load `model.joblib` and, with `PYTHONPATH=src`, reproduce the notebook demo through `recommend_next_best_action()` with metadata parameters (`CLI-P21780PQ8D9W` → `ACTION`, Tarjeta Crédito, Push, propensity ≈ 0.008406, expected value ≈ 26.79); verify with a throwaway script run outside the repo.
- [ ] 1.3 Pin those exact versions in `requirements.txt` next to FastAPI and Uvicorn, and add `requirements-dev.txt` with pytest and httpx; verify a fresh venv installs both files and `python -m pip check` passes.

## 2. Artifact loading and settings

- [ ] 2.1 Add `app/nba/settings.py`, which resolves `ARTIFACTS_DIR` (default `./artifacts/propensity`) and the four artifact paths; verify with unit tests for the default and overridden values.
- [ ] 2.2 Add `app/nba/loader.py`, which loads the model, catalog, snapshot, and metadata into an immutable bundle, checks the required metadata keys, builds the `customer_id → row position` index, and raises an error naming the missing or unreadable path; verify with unit tests using temporary files (valid bundle, missing snapshot, metadata missing keys).

## 3. Recommendation service and schemas

- [ ] 3.1 Add `app/nba/schemas.py` with the response and candidate Pydantic models: a `decision` `Literal` of the four engine values, nullable economic fields, `country`, `candidates: list | None`, and field descriptions that mark `propensity` as a raw, uncalibrated score; verify the schema renders in `NextBestActionResponse.model_json_schema()`.
- [ ] 3.2 Add `app/nba/service.py` (`NBAService.recommend(customer_id, include_candidates)`). It raises `CustomerNotFound` without calling the engine, calls `recommend_next_best_action()` with metadata parameters, maps fields, takes the top 5 candidates by rank, and converts numpy, NaN, and infinity to JSON-safe values. Verify with unit tests that use a stub model and small in-memory frames for each decision value (`ACTION`, `NO_ACTION_CONSENT`, `NO_ACTION_NO_SUPPORTED_CANDIDATES`, `NO_ACTION_NEGATIVE_VALUE`), unknown customers, candidates on, off, and empty, and strict JSON serialization (`allow_nan=False`).

## 4. HTTP endpoint and startup wiring

- [ ] 4.1 Add `app/nba/router.py` with a sync `GET /customers/{customer_id}/next-best-action`, an `include_candidates: bool = False` query parameter, `response_model`, and a documented 404 response; register it in `app/main.py`. Wire a lifespan that builds `NBAService` once and stores it on `app.state`, plus a `get_nba_service` dependency. Verify with TestClient tests that use `dependency_overrides`: 200 for a known ID, 404 with `detail` for an unknown ID, 200 for a NO_ACTION decision, candidates behavior, and OpenAPI containing the path, both parameters, the 200 schema, and the 404 response.
- [ ] 4.2 Verify fail-fast startup. A TestClient test with `ARTIFACTS_DIR` pointing at an empty temp dir raises at startup with the missing path, and `/health` still returns exactly `{"status":"ok"}` when artifacts are present.
- [ ] 4.3 Add an integration test, skipped when artifacts are absent, that compares the endpoint with a direct `recommend_next_best_action()` call for the demo customer, a consent-false customer, and at least 20 other snapshot customers; verify it passes locally with `PYTHONPATH=src pytest`.
- [ ] 4.4 Update README with artifact setup from Drive, `ARTIFACTS_DIR`, the `PYTHONPATH=src` local command, endpoint examples (200 ACTION, 200 NO_ACTION, 404, `include_candidates=true`), and how to run the tests; verify every documented command runs as written.

## 5. Container packaging

- [ ] 5.1 Update `.dockerignore` to also allow `src/propensity/**` (excluding caches) while keeping `artifacts/`, notebooks, env files, and Git excluded. Update `Dockerfile` to copy `src/propensity/`, set `PYTHONPATH=/app/src` and `ARTIFACTS_DIR=/app/artifacts/propensity`, and keep the non-root user and no reload. Verify that `docker build -t factored-nba .` succeeds and `docker run --rm --entrypoint sh factored-nba -c 'id -u; find . -type f'` shows a nonzero UID with only `app/`, `src/propensity/`, and `requirements.txt` files.
- [ ] 5.2 Run `docker run -p 8000:8000 -v "$PWD/artifacts/propensity:/app/artifacts/propensity:ro" factored-nba` and repeat the health, docs, OpenAPI, 200, and 404 checks against port 8000. Then run without the mount and confirm startup fails and names the missing artifact. Add both commands and the expected failure to README.

## 6. Integration and scope checks

- [ ] 6.1 Review the final diff: `src/propensity/` is unchanged since `32293b3`, no artifact or final-test file is tracked or copied into the image, no notebook changed, and no training, calibration, or LangGraph code is reachable from `app/`. Run the full test suite and `openspec validate add-next-best-action-api --strict`.
