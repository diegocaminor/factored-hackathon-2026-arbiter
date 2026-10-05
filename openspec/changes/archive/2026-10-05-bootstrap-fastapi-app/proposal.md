# Proposal

## Why

The hackathon repository has experimental notebooks but no runnable application boundary. A minimal HTTP service establishes local and Docker execution before integrating the existing decision pipeline.

## What Changes

- Add a FastAPI application under `app/` with `GET /health` returning HTTP 200 and `{"status": "ok"}`.
- Expose the default Swagger UI at `/docs` and OpenAPI document at `/openapi.json`.
- Add `requirements.txt`, `Dockerfile`, and `.dockerignore` for a small, independent runtime.
- Document local startup with `uvicorn app.main:app --reload`, Docker build/run commands, and smoke checks in the existing README.
- Leave notebooks, propensity code, and ML artifacts unchanged. Do not add ML, LangGraph, UI, or external-service integration.

## Capabilities

### New Capabilities

- `http-service`: An independently runnable HTTP service with liveness reporting, API documentation, and equivalent local/container behavior.

### Modified Capabilities

None.

## Impact

Adds `app/__init__.py`, `app/main.py`, `requirements.txt`, `Dockerfile`, and `.dockerignore`; updates `README.md`. Introduces FastAPI and Uvicorn runtime dependencies. No existing API, data, or model contract changes. The scaffold must start without propensity code, model artifacts, or credentials.
