# Proposal

## Why

Every capability of the solution (frozen NBA engine, confirm and handoff, LangGraph workflow) is reachable only through Swagger or `curl`, which makes a live hackathon demo slow and hard to follow. A small, polished single page served by the existing FastAPI app can walk through the whole flow in one screen, with no new runtime pieces to start or break.

## What Changes

- Serve a static demo UI from the existing FastAPI app: `GET /` returns `index.html`, and assets are served under `/static/*` from `app/static/`. The UI shares an origin with the API, so CORS is not needed. There is no build step, no new dependency, and no CDN, so the page works offline.
- The page lets the user pick a demo preset or type any `customer_id`, then calls `GET /customers/{id}/next-best-action?include_candidates=true`. It shows a recommendation card (decision, country, product, channel, raw propensity, expected value, historical support) and the top 5 candidate actions.
- Confirm calls `POST /customers/{id}/confirm` and is disabled unless the runtime decision is `ACTION`. Handoff calls `POST /customers/{id}/handoff` with an optional reason. The execution result is shown on the page.
- A LangGraph panel runs `POST /agent/run` with a `user_confirmed` toggle and highlights the workflow path, derived only from the response `status`. No tracing or observability endpoint is added.
- Demo presets: `CLI-P21780PQ8D9W` and `CLI-S5RL0QD6GG1U` are labeled ACTION; `CLI-P8F6JG7TN8YN` and `CLI-QHXK2HCRNFBI` are labeled NO CONSENT. These were checked against the real artifacts. Labels are hints only; the displayed decision always comes from the API at runtime.
- 404, 409, 422, and connection failures are shown as visible messages on the page.
- A header link to `/docs` and a manual demo checklist in README.

**Backend wiring note:** serving the UI requires mounting `app/static/` and adding `GET /` in `app/main.py`, about 5 lines. No business logic, data API, customer-discovery endpoint, or graph-tracing endpoint is added.

Out of scope: React, Vite, Streamlit, or any frontend toolchain; frontend testing frameworks or contract testing; authentication; new backend endpoints; any import of ML modules or artifact access from the UI.

## Capabilities

### New Capabilities

- `demo-ui`: A browser page served by the service that demonstrates recommendation, execution, handoff, and the agent workflow using only the existing HTTP API.

### Modified Capabilities

None. `http-service`, `next-best-action`, `offer-execution`, and `agent-orchestration` requirements are unchanged.

## Impact

- Code: new `app/static/index.html`, `app/static/app.js`, and `app/static/styles.css`. `app/main.py` mounts static files and serves `GET /`.
- Container: no Dockerfile or `.dockerignore` change, since the allowlist already includes `app/**`.
- Dependencies: none.
- Tests: TestClient checks for `GET /` and the static assets, plus an assertion that `app.js` references only the existing API endpoints.
- Docs: README gains the UI URL and a manual demo checklist.
