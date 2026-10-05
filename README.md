# Arbiter

AI-first banking customer-service agent — built for the [Factored AI & Data Hackathon 2026](https://www.factored.ai/careers/ai-data-hackathon).

## Challenge

Build a focused AI-first workflow for banking customer service (e.g. account inquiries, card support, disputes, or credit eligibility) that goes beyond a chatbot: understanding, decision-making, action, verification, and escalation.

## Requirements

- Multilingual support (Spanish and Portuguese)
- Production-readiness over feature breadth
- Documented trade-offs: autonomy, accuracy, latency, cost, human oversight

## Deliverables

- [ ] Deployed solution (shareable link)
- [ ] 4–6 slide presentation
- [ ] Video pitch (max 3 min)

## Status

🚧 In progress — Challenge period: Sep 25 – Oct 5, 2026

## HTTP service

A FastAPI service under `app/` exposes the frozen Next Best Action (NBA) engine from `src/propensity/` (notebooks 08–09), plus simulated confirm and handoff actions. `GET /health` reports **HTTP application liveness only**: it does not check model readiness. The service loads the model and pre-test data once at startup and refuses to start if any required artifact is missing.

### Model artifacts

Artifacts are not versioned (`artifacts/` is git-ignored). Copy these files from the project's Google Drive `artifacts/propensity/` folder, keeping the same relative paths:

```
artifacts/propensity/
  final_evaluation/catboost_20261004_222052/model.joblib
  nba/action_catalog_pretest.parquet
  nba/customer_snapshot_pretest.parquet
  nba/nba_metadata.json
```

The service reads them from `ARTIFACTS_DIR`, which defaults to `./artifacts/propensity` relative to the working directory. Google Drive is only the source for populating this folder; it is not used at runtime. Do not copy final-test files (`scored_test.parquet`, `FINAL_TEST_EVALUATED.json`, `test_deciles.csv`) or the Platt calibrator; the service never uses them.

### Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

### Run locally

```bash
PYTHONPATH=src uvicorn app.main:app --reload
```

`PYTHONPATH=src` makes the vendored `propensity` package importable. To use artifacts stored elsewhere, prefix the command with `ARTIFACTS_DIR=/path/to/artifacts/propensity`.

- Health: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI document: http://127.0.0.1:8000/openapi.json
- Next best action: http://127.0.0.1:8000/customers/CLI-P21780PQ8D9W/next-best-action

Swagger UI loads its assets from a public CDN by default, so a browser with internet access is required to view `/docs`.

Startup takes a few seconds while the model and the 150k-row customer snapshot load. Without artifacts, startup fails with `ArtifactLoadError: Required NBA artifact not found: <path>`.

### Next best action endpoint

`GET /customers/{customer_id}/next-best-action[?include_candidates=true]`

| Status | When |
|---|---|
| 200 | Customer exists in the pre-test snapshot, including every `NO_ACTION_*` decision |
| 404 | Customer ID is not in the snapshot |

`decision` is one of `ACTION`, `NO_ACTION_CONSENT`, `NO_ACTION_NO_SUPPORTED_CANDIDATES`, or `NO_ACTION_NEGATIVE_VALUE`. Fields the engine does not produce for a decision are `null`. `propensity` is the **raw, uncalibrated** model score used for ranking. Economic values are in the local currency of `country`; never sum them across countries.

```bash
curl -s http://127.0.0.1:8000/customers/CLI-P21780PQ8D9W/next-best-action
# {"customer_id":"CLI-P21780PQ8D9W","country":"Argentina","decision":"ACTION",
#  "product":"Tarjeta Crédito","channel":"Push","propensity":0.008405942144870617,
#  "expected_conversion_value":3186.94,"estimated_send_cost":0.0005,
#  "expected_value":26.788733259173966,"historical_support":5887,"candidates":null}

curl -s http://127.0.0.1:8000/customers/CLI-P8F6JG7TN8YN/next-best-action
# {"customer_id":"CLI-P8F6JG7TN8YN","country":"Argentina","decision":"NO_ACTION_CONSENT",
#  "product":null,"channel":null,"propensity":null,...,"candidates":null}

curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/customers/CLI-DOES-NOT-EXIST/next-best-action
# 404  (body: {"detail":"Customer not found: CLI-DOES-NOT-EXIST"})

curl -s 'http://127.0.0.1:8000/customers/CLI-P21780PQ8D9W/next-best-action?include_candidates=true'
# "candidates": up to 5 ranked actions, each with rank, product, channel,
# propensity, expected_conversion_value, estimated_send_cost, expected_value,
# historical_support
```

### Confirm and handoff endpoints

After a recommendation, a client either confirms it, which simulates sending the offer, or escalates the customer to a human. Both actions are **simulated**: no SMS, Push, WhatsApp, or other provider is contacted. Both are **stateless**: nothing is persisted, and repeated confirms simulate repeated sends with the same `provider_message_id`.

`POST /customers/{customer_id}/confirm` takes no body. The server recomputes the recommendation and sends its product and channel.

| Status | When |
|---|---|
| 200 | Current decision is `ACTION`; returns `status` `SIMULATED_SENT`, `customer_id`, `product`, `channel`, `provider_message_id` |
| 409 | Customer exists but the current decision is a `NO_ACTION_*` value |
| 404 | Customer ID is not in the snapshot |

`POST /customers/{customer_id}/handoff` takes an optional JSON body `{"reason": string | null}`. When it is absent or null, the reason defaults to `Customer did not confirm automated execution.`. Handoff works for any known customer, whatever the decision.

| Status | When |
|---|---|
| 200 | Customer exists; returns `status` `HANDOFF_CREATED`, `customer_id`, `reason`, `queue` (`sales-assistance`) |
| 422 | Body is not a JSON object, or `reason` is not a string or null |
| 404 | Customer ID is not in the snapshot |

```bash
curl -s -X POST http://127.0.0.1:8000/customers/CLI-P21780PQ8D9W/confirm
# {"status":"SIMULATED_SENT","customer_id":"CLI-P21780PQ8D9W","product":"Tarjeta Crédito",
#  "channel":"Push","provider_message_id":"demo-CLI-P21780PQ8D9W-Push"}

curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/customers/CLI-P8F6JG7TN8YN/confirm
# {"detail":"Customer CLI-P8F6JG7TN8YN has no actionable recommendation (decision: NO_ACTION_CONSENT)"}
# 409

curl -s -X POST http://127.0.0.1:8000/customers/CLI-P8F6JG7TN8YN/handoff
# {"status":"HANDOFF_CREATED","customer_id":"CLI-P8F6JG7TN8YN",
#  "reason":"Customer did not confirm automated execution.","queue":"sales-assistance"}

curl -s -X POST http://127.0.0.1:8000/customers/CLI-P21780PQ8D9W/handoff \
  -H 'Content-Type: application/json' -d '{"reason": "Customer asked for an advisor"}'
# {"status":"HANDOFF_CREATED","customer_id":"CLI-P21780PQ8D9W",
#  "reason":"Customer asked for an advisor","queue":"sales-assistance"}
```

### Smoke checks

```bash
curl -i http://127.0.0.1:8000/health
# HTTP/1.1 200 OK ... {"status":"ok"}

curl -f http://127.0.0.1:8000/docs

curl -fsS http://127.0.0.1:8000/openapi.json \
  | python -c 'import json,sys; p=json.load(sys.stdin)["paths"]; assert "get" in p["/health"]; assert "get" in p["/customers/{customer_id}/next-best-action"]'
```

Editing and saving a file under `app/` triggers an automatic reload while `--reload` is running.

### Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

`pytest.ini` puts the repository root and `src/` on the import path. Unit tests use a stub model and in-memory data. `tests/nba/test_integration.py` compares the endpoint with direct `recommend_next_best_action()` calls on the real artifacts, and is skipped when they are absent.

### Run in Docker

```bash
docker build -t factored-nba .
docker run -p 8000:8000 \
  -v "$PWD/artifacts/propensity:/app/artifacts/propensity:ro" \
  factored-nba
```

The image contains `app/` and `src/propensity/` but never the artifacts. They are mounted read-only at the image's `ARTIFACTS_DIR` (`/app/artifacts/propensity`). No Compose file, host ML dependencies, or application credentials are required. The container runs as a non-root user with a single Uvicorn process and no reload.

Repeat the smoke checks and endpoint examples above against `http://127.0.0.1:8000`.

Running without the mount fails at startup by design (exit code 3):

```bash
docker run --rm factored-nba
# app.nba.loader.ArtifactLoadError: Required NBA artifact not found:
#   /app/artifacts/propensity/final_evaluation/catboost_20261004_222052/model.joblib
# ERROR:    Application startup failed. Exiting.
```
