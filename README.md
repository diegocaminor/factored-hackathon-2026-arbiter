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

## For reviewers: where to look

**Live demo:** https://arbiter.diegocamino.com — the **Decision Engine** tab shows what the bank decides for a customer, and the **Customer Agent** tab shows the conversation the customer has. Start with a demo preset such as `CLI-P21780PQ8D9W`.

Suggested reading order: the workflow discovery document, then the benchmark matrix, then the notebooks, then the service code.

### Product discovery (`product-discovery/`)

| File | What it contains |
|---|---|
| [`Factored Hackathon - Workflow Discovery - Next Best Action.docx`](product-discovery/Factored%20Hackathon%20-%20Workflow%20Discovery%20-%20Next%20Best%20Action.docx) | The reasoning behind the solution: why the initial fraud-detection idea was dropped (weak supporting signal in the synthetic data), the pivot to marketing Next Best Action, validation on the full history of 1.75M campaign sends, product × channel and economic signal, data anomalies (WhatsApp and Voice never convert), the proposed architecture, the AI agent's role, and modeling guardrails. |
| [`Factored Hackathon - Baseline Benchmark Matrix.xlsx`](product-discovery/Factored%20Hackathon%20-%20Baseline%20Benchmark%20Matrix.xlsx) | The baselines the model is measured against. **Baseline Matrix**: conversion by product and channel, plus global, channel, and per-country economic baselines. **Economic Examples**: net value per send by country, product, and best channel. **Benchmark Notes**: how each baseline is defined and used. **Arbiter Economic Simulation**: top-decile lift (1.335 on the untouched test set) and the resulting ~25% fewer contacts for the same number of conversions, with the caveats that keep it from being read as production ROI. |

### Analysis and modeling notebooks (`notebooks-discovery/`)

Run in order; each one consumes the output of the previous ones.

| Notebook | Purpose |
|---|---|
| [`01_eda_latam_bank_dataset`](notebooks-discovery/01_eda_latam_bank_dataset.ipynb) | Exploration of the LATAM bank dataset on S3. |
| [`02_marketing_next_best_action`](notebooks-discovery/02_marketing_next_best_action.ipynb) | Checks whether conversion varies enough by campaign, product, channel, and customer to support a Next Best Action workflow. |
| [`03_decision_dataset_preparation`](notebooks-discovery/03_decision_dataset_preparation.ipynb) | Builds the modeling dataset: one row per customer × product × channel × send time. |
| [`04_propensity_model_training`](notebooks-discovery/04_propensity_model_training.ipynb) | Baseline propensity model for `P(conversion \| customer, product, channel, context)` with time-aware splits. |
| [`05_propensity_model_experiments`](notebooks-discovery/05_propensity_model_experiments.ipynb) | Logistic-regression experiments; they showed almost no ranking signal. |
| [`06_catboost_propensity_experiments`](notebooks-discovery/06_catboost_propensity_experiments.ipynb) | Switches to CatBoost to learn non-linear interactions between customer, product, channel, and context. |
| [`07_final_holdout_and_calibration`](notebooks-discovery/07_final_holdout_and_calibration.ipynb) | Freezes the selected CatBoost model, calibrates on validation only, and evaluates the test set exactly once. |
| [`08_next_best_action_engine`](notebooks-discovery/08_next_best_action_engine.ipynb) | The decision engine: scores product × channel candidates and ranks them by expected value. |
| [`09_langgraph_nba_agent`](notebooks-discovery/09_langgraph_nba_agent.ipynb) | Wraps the engine in a LangGraph workflow in which the language layer never invents product, channel, or values. |

### Service and specifications

| Path | What it contains |
|---|---|
| `app/` | FastAPI service: NBA endpoint, simulated confirm and handoff, LangGraph workflow, conversational agent, and the demo UI. Details below. |
| `src/propensity/` | The frozen NBA engine and LangGraph graph used by notebooks 08–09 and by the service. |
| `openspec/specs/` | Behavior specifications for each capability (`next-best-action`, `offer-execution`, `agent-orchestration`, `conversational-agent`, `http-service`, `demo-ui`). |
| `openspec/changes/archive/` | Each change as it was planned: proposal, design decisions, and tasks. |
| `tests/` | Automated tests (248), runnable without the provider key or the real artifacts. |

## HTTP service

A FastAPI service under `app/` exposes the frozen Next Best Action (NBA) engine from `src/propensity/` (notebooks 08–09), plus simulated confirm and handoff actions and the LangGraph workflow (`POST /agent/run`). `GET /health` reports **HTTP application liveness only**: it does not check model readiness. The service loads the model and pre-test data once at startup and refuses to start if any required artifact is missing.

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

### Agent workflow endpoint

`POST /agent/run` runs the LangGraph workflow from `src/propensity/langgraph_nba_agent.py` once per request: load customer → NBA recommendation → ACTION/NO_ACTION routing → confirmation gate → simulated execution or human handoff. The graph contains **no LLM**. The CatBoost model and the NBA engine decide product, channel, propensity, and expected value, and `assistant_message` is a template filled with those values. The run is **stateless**: no checkpointer, thread ID, or persisted graph state. Use `GET /customers/{customer_id}/next-best-action` to preview a recommendation before deciding.

Request body (both fields required; `user_confirmed` must be a JSON boolean):

```json
{"customer_id": "CLI-P21780PQ8D9W", "user_confirmed": true}
```

| Decision | `user_confirmed` | `status` | `execution_result` |
|---|---|---|---|
| `ACTION` | `true` | `COMPLETED` | Same body as `POST /customers/{id}/confirm` |
| `ACTION` | `false` | `HANDOFF` | Same body as `POST /customers/{id}/handoff` (default reason) |
| `NO_ACTION_*` | either | the decision | `null` |

| HTTP status | When |
|---|---|
| 200 | Customer exists (every routing outcome above) |
| 404 | Customer ID is not in the snapshot; the graph is not invoked |
| 422 | Body missing, not an object, missing a field, or `user_confirmed` not a JSON boolean (`"true"` and `1` are rejected) |

`recommendation` uses the same field names and values as `GET /customers/{id}/next-best-action`. The raw snapshot row and ranked catalog rows are never returned.

```bash
curl -s -X POST http://127.0.0.1:8000/agent/run \
  -H 'Content-Type: application/json' -d '{"customer_id": "CLI-P21780PQ8D9W", "user_confirmed": true}'
# {"customer_id":"CLI-P21780PQ8D9W","user_confirmed":true,"status":"COMPLETED",
#  "recommendation":{"decision":"ACTION","product":"Tarjeta Crédito","channel":"Push",
#    "propensity":0.008405942144870617,"expected_conversion_value":3186.94,
#    "estimated_send_cost":0.0005,"expected_value":26.788733259173966,"historical_support":5887},
#  "consent_required":true,
#  "product_details":{"name":"Tarjeta Crédito","summary":"Línea de crédito revolvente para compras y pagos."},
#  "execution_result":{"status":"SIMULATED_SENT","customer_id":"CLI-P21780PQ8D9W","product":"Tarjeta Crédito",
#    "channel":"Push","provider_message_id":"demo-CLI-P21780PQ8D9W-Push"},
#  "assistant_message":"Offer simulated successfully for Tarjeta Crédito via Push."}

curl -s -X POST http://127.0.0.1:8000/agent/run \
  -H 'Content-Type: application/json' -d '{"customer_id": "CLI-P21780PQ8D9W", "user_confirmed": false}'
# {..."status":"HANDOFF",...,"execution_result":{"status":"HANDOFF_CREATED",
#  "customer_id":"CLI-P21780PQ8D9W","reason":"Customer did not confirm automated execution.",
#  "queue":"sales-assistance"},"assistant_message":"No automated send performed. A human handoff was created."}

curl -s -X POST http://127.0.0.1:8000/agent/run \
  -H 'Content-Type: application/json' -d '{"customer_id": "CLI-P8F6JG7TN8YN", "user_confirmed": true}'
# {..."status":"NO_ACTION_CONSENT",...,"execution_result":null,
#  "assistant_message":"No outbound action recommended. Decision: NO_ACTION_CONSENT."}
```

The minimum historical sends threshold has a single source: `min_historical_sends` in `nba_metadata.json`. Startup fails if it is missing or not a positive integer. The NBA endpoint and the agent both read it from there.

**Notebook 09 compatibility:** `AgentContext` now requires `min_historical_sends` and has no default. If notebook 09 is rerun against this repository's `src/propensity`, pass it explicitly:

```python
AgentContext(..., customer_id_col=customer_id_col, min_historical_sends=metadata["min_historical_sends"])
```

### Conversational agent endpoint

`POST /agent/chat` runs one customer-facing chat turn. An LLM does two things only: it classifies the intent of the customer's latest message, and it writes the reply. Application code decides and executes everything in between, and the NBA engine is recomputed on every turn, so product, channel, and decision always come from the engine.

The endpoint is **stateless**: send the full history on every request, oldest first, ending with a `user` message (at most 20 messages, 2,000 characters each). Nothing is stored between requests.

| Intent | What the service does | `action_taken` |
|---|---|---|
| `REQUEST_RECOMMENDATION`, `ASK_WHY`, `ASK_PRODUCT` | Nothing; the reply explains the offer | `NONE` |
| `CONFIRM` with decision `ACTION` | Simulated send, same as `POST /customers/{id}/confirm` | `OFFER_CONFIRMED` |
| `CONFIRM` without an `ACTION` decision | Nothing; the reply asks for clarification | `NONE` |
| `DECLINE` | Nothing; no automatic handoff | `NONE` |
| `REQUEST_HUMAN` | Handoff with reason `Customer requested human assistance via chat.` | `HANDOFF_CREATED` |
| `UNCLEAR` | Nothing; the reply asks a clarifying question | `NONE` |

**Data minimization.** The LLM receives only the conversation and a customer-safe view: whether an offer exists, product, product summary, channel, country, and a safe outcome of the executed action. It never receives propensity, economic values, candidate rankings, historical support, decision codes, customer model features (such as gender, marital status, income, or credit score), or system names. As a second layer, a reply that names an internal term is replaced with a fixed safe reply. For non-`ACTION` decisions, such as `NO_ACTION_CONSENT`, the agent presents no offer and offers an advisor instead.

**Configuration.** Chat is optional and needs an OpenAI API key:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables chat. Without it, `/agent/chat` answers 503 and every other endpoint works as usual. |
| `CHAT_MODEL` | Optional model ID. Defaults to `gpt-4o-mini`. |

```bash
OPENAI_API_KEY=sk-... PYTHONPATH=src uvicorn app.main:app --reload
```

Without a key:

```bash
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[{"role":"user","content":"Hi"}]}'
# 503 {"detail":"Chat agent is unavailable: no LLM provider is configured."}
```

With a key (reply wording varies between runs; the other fields do not):

```bash
# Recommendation
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[{"role":"user","content":"What do you recommend for me?"}]}'
# {"customer_id":"CLI-P21780PQ8D9W","reply":"...Tarjeta Crédito...",
#  "intent":"REQUEST_RECOMMENDATION","action_taken":"NONE","execution_result":null}

# Why it is relevant
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[{"role":"user","content":"Why is this a good fit for me?"}]}'
# "intent":"ASK_WHY","action_taken":"NONE"

# Confirm, with history sent by the client
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[
        {"role":"user","content":"What do you recommend for me?"},
        {"role":"assistant","content":"I can suggest a credit card, Tarjeta Crédito."},
        {"role":"user","content":"Yes, please send it to me."}]}'
# "intent":"CONFIRM","action_taken":"OFFER_CONFIRMED",
# "execution_result":{"status":"SIMULATED_SENT",...,"provider_message_id":"demo-CLI-P21780PQ8D9W-Push"}

# Decline
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[{"role":"user","content":"No thanks, I am not interested."}]}'
# "intent":"DECLINE","action_taken":"NONE","execution_result":null

# Human assistance
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P21780PQ8D9W","messages":[{"role":"user","content":"Quiero hablar con un asesor"}]}'
# "intent":"REQUEST_HUMAN","action_taken":"HANDOFF_CREATED",
# "execution_result":{"status":"HANDOFF_CREATED",...,"reason":"Customer requested human assistance via chat.","queue":"sales-assistance"}

# NO CONSENT customer: no offer is presented and nothing is sent, even when they say yes
curl -s -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"CLI-P8F6JG7TN8YN","messages":[{"role":"user","content":"Yes, send it"}]}'
# "intent":"CONFIRM","action_taken":"NONE","execution_result":null
```

Other errors: 404 for an unknown customer (no LLM call), 422 for an invalid body, and 502 when the provider fails before any action ran. If the provider fails after an action ran, the response is still 200 with the real action fields and a fixed bilingual reply.

### Demo UI

With the service running, open `http://127.0.0.1:8000/`. The page is plain HTML, JavaScript, and CSS under `app/static/`, served by the same FastAPI app: no build step, no extra process, no CDN. It calls only the five endpoints above and never touches ML code or artifacts. The header links to `/docs`.

The customer bar is shared by two tabs: **Decision Engine** (selected by default) shows what the bank decides, and **Customer Agent** shows what the customer hears. Switching tabs never reloads data.

| Panel | What it does |
|---|---|
| Customer bar (shared) | Pick a demo preset or type any customer ID, then Load. Calls `GET /customers/{id}/next-best-action?include_candidates=true`. |
| Recommendation | Decision badge, country, product, channel, propensity (raw score), expected value in local currency, and historical support. Missing values show as `—`. |
| Top 5 candidate actions | Ranked candidates from the same response; the top row is highlighted. |
| Execute | **Confirm offer** calls `POST /customers/{id}/confirm`, enabled only when the decision is `ACTION`. **Hand off to human** calls `POST /customers/{id}/handoff` with the optional reason. The execution result appears below. |
| LangGraph workflow | Calls `POST /agent/run` with the `user_confirmed` toggle and highlights the path derived from the returned `status`, with the assistant message and execution result. |
| Customer Agent tab | Chat with the loaded customer through `POST /agent/chat`. Replies are shown exactly as the backend writes them; the page adds no logic. History lives only in page memory, the latest 20 messages are sent each turn, and the chat resets when a different customer is loaded. Requires `OPENAI_API_KEY` on the server (see [Conversational agent endpoint](#conversational-agent-endpoint)). |
| Debug (last turn) | Beside the chat, for presenters only: the last turn's intent, action taken, and execution result. Never part of the customer conversation. |
| Error banner | Shows 404, 409, 422, 502, and 503 responses with the API's `detail`, and connection errors when the server is unreachable. A chat message that fails returns to the input. |

Demo presets:

| Customer ID | Label |
|---|---|
| `CLI-P21780PQ8D9W` | ACTION |
| `CLI-S5RL0QD6GG1U` | ACTION |
| `CLI-P8F6JG7TN8YN` | NO CONSENT |
| `CLI-QHXK2HCRNFBI` | NO CONSENT |

Labels are hints only. The decision shown always comes from the API at runtime. In real data only `ACTION` and `NO_ACTION_CONSENT` occur; the `NO_ACTION_NEGATIVE_VALUE` and `NO_ACTION_NO_SUPPORTED_CANDIDATES` paths are covered by backend tests and cannot be shown in the live demo.

#### Manual demo checklist

Run against the Docker image with mounted artifacts (see [Run in Docker](#run-in-docker)), using a named container so the last steps work. The Customer Agent steps need a `.env` file with `OPENAI_API_KEY`:

```bash
docker build -t factored-nba .
docker run -d --name nba-ui -p 8000:8000 --env-file .env \
  -v "$PWD/artifacts/propensity:/app/artifacts/propensity:ro" \
  factored-nba
```

| # | Action | Expected |
|---|---|---|
| 1 | Open `http://127.0.0.1:8000/` | Header "Arbiter" with the API docs link, four presets with ACTION or NO CONSENT badges, action buttons disabled |
| 2 | Click preset `CLI-P21780PQ8D9W` | Badge `ACTION`, Argentina, Tarjeta Crédito, Push, propensity 0.0084, expected value 26.79 (Argentina), support 5,887, five candidate rows with #1 highlighted |
| 3 | Click **Confirm offer** | Execution result `SIMULATED_SENT` with `demo-CLI-P21780PQ8D9W-Push` |
| 4 | Click **Hand off to human** with an empty reason | `HANDOFF_CREATED`, the default reason, queue `sales-assistance` |
| 5 | Type a reason and hand off again | `HANDOFF_CREATED` with the typed reason |
| 6 | **Run agent** with the toggle on | Status `COMPLETED`, path Load customer → Recommend → Prepare offer → Execute offer |
| 7 | Turn the toggle off and **Run agent** | Status `HANDOFF`, path ending in Human handoff |
| 8 | Click preset `CLI-P8F6JG7TN8YN` | Badge `NO_ACTION_CONSENT`, dashes in the metrics, empty candidates, Confirm disabled with "Only ACTION recommendations can be confirmed." |
| 9 | **Run agent** on that customer | Status `NO_ACTION_CONSENT`, path ending in No action |
| 10 | Type `NO-EXISTE` and Load | Error banner "Not found: Customer not found: NO-EXISTE" |
| 11 | Type `CLI-S5RL0QD6GG1U` and Load | Loads as `ACTION` |
| 12 | Open **Customer Agent**, then go back to **Decision Engine** | `CLI-S5RL0QD6GG1U` still loaded in both; nothing reloads |
| 13 | Load `CLI-P21780PQ8D9W`, open **Customer Agent**, send "What do you recommend for me?" | Your message on the right, a typing indicator, then a reply presenting Tarjeta Crédito; debug shows `REQUEST_RECOMMENDATION`, `NONE` |
| 14 | Send "Why is this a good fit for me?" | A general, account-based reason with no personal facts or internal terms |
| 15 | Send "Yes, please send it to me." | Reply confirms the offer was sent; debug shows `CONFIRM`, `OFFER_CONFIRMED`, `SIMULATED_SENT` |
| 16 | Send "¿Puedo hablar con un asesor?" | Reply in Spanish; debug shows `REQUEST_HUMAN`, `HANDOFF_CREATED` |
| 17 | Load preset `CLI-P8F6JG7TN8YN` | The chat is empty again |
| 18 | Send "Yes, send it" | No offer is presented and an advisor is offered; debug shows `CONFIRM`, `NONE` |
| 19 | Run `docker stop nba-ui`, then Load | Error banner "Connection error: the API could not be reached..." |
| 20 | Run `docker rm nba-ui`, start it again without `--env-file .env`, load a customer, and send a chat message | Error banner "Unavailable: Chat agent is unavailable: no LLM provider is configured."; the message returns to the input |

Clean up with `docker rm -f nba-ui`.

### Smoke checks

```bash
curl -i http://127.0.0.1:8000/health
# HTTP/1.1 200 OK ... {"status":"ok"}

curl -f http://127.0.0.1:8000/docs

curl -fsS http://127.0.0.1:8000/openapi.json \
  | python -c 'import json,sys; p=json.load(sys.stdin)["paths"]; assert "get" in p["/health"]; assert "get" in p["/customers/{customer_id}/next-best-action"]; assert "post" in p["/agent/run"]'
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

The image contains `app/` and `src/propensity/` but never the artifacts. They are mounted read-only at the image's `ARTIFACTS_DIR` (`/app/artifacts/propensity`). No Compose file or host ML dependencies are required, and no credentials are baked into the image. The container runs as a non-root user with a single Uvicorn process and no reload.

To enable the conversational agent, pass the key at run time:

```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -v "$PWD/artifacts/propensity:/app/artifacts/propensity:ro" \
  factored-nba
```

Repeat the smoke checks and endpoint examples above against `http://127.0.0.1:8000`.

Running without the mount fails at startup by design (exit code 3):

```bash
docker run --rm factored-nba
# app.nba.loader.ArtifactLoadError: Required NBA artifact not found:
#   /app/artifacts/propensity/final_evaluation/catboost_20261004_222052/model.joblib
# ERROR:    Application startup failed. Exiting.
```
