# Design

## Context

See `proposal.md` for motivation and `specs/demo-ui/spec.md` for behavior. Current state:

- `app/main.py` registers the NBA, execution, and agent routers. No route exists at `/`.
- The Docker build context allowlist already includes `app/**`, and the Dockerfile copies `app/`, so new files under `app/static/` reach the image without packaging changes.
- In a sample of 3,000 real customers, only `ACTION` (about 52%) and `NO_ACTION_CONSENT` (about 48%) occur. The other two NO_ACTION paths are covered by synthetic backend tests, not by the live demo.
- The existing API already returns everything the page needs, including the agent `status` from which the graph path can be derived.

## Goals / Non-Goals

**Goals:** One screen and one process, readable from across a room. No new dependencies. Works offline. Cannot reach ML code or artifacts.

**Non-Goals:** No SPA framework, routing, state library, bundler, i18n, auth, or responsive redesign beyond a sensible layout. No backend observability for the graph.

## Decisions

1. **Vanilla HTML, JS, and CSS served by FastAPI.** *Alternatives:* Streamlit (a second server process and port, a rerun model that fights button flows, and a Python runtime where an ML `import` is one line away) and React/Vite (Node toolchain, build step, and a CORS proxy for one page). Rejected for added moving parts with no demo benefit.

2. **Serving.** `app.mount("/static", StaticFiles(directory=<app>/static), name="static")`, with the path resolved relative to `app/main.py` so it works from any working directory. A plain `GET /` returns `FileResponse(index.html)` with `include_in_schema=False`, so Swagger stays API-only. Both are declared after the API routers.

3. **Files.** `index.html` (structure and semantic sections), `styles.css` (system font stack, CSS variables, cards, table, disabled and error states), and `app.js` (one ES module, no globals beyond what's needed). The UI strings are in English, matching the API.

4. **A single API client function.** `api(method, path, body?)` wraps `fetch`, parses JSON, and maps outcomes to typed results: OK, HTTP error with status and `detail` (404, 409, 422, or 500), or connection error from a rejected `fetch`. Every call site renders errors through one `showError()` banner. The four endpoint paths are built in one place, which keeps the "only existing endpoints" test trivial.

5. **The decision drives the controls.** After a successful load, the page stores `{customerId, decision}`. Confirm is enabled only when `decision === "ACTION"`; otherwise it is disabled with a visible hint. Confirm, Handoff, and Run agent all require a loaded customer, so loading a different ID resets the result panels.

6. **Agent path derived from `status` only.** A static node list (`load_customer`, `recommend`, `prepare_offer`, `execute_offer`, `handoff`, `no_action`) and a lookup map: `COMPLETED` → `[load_customer, recommend, prepare_offer, execute_offer]`, `HANDOFF` → `[load_customer, recommend, prepare_offer, handoff]`, `NO_ACTION_*` → `[load_customer, recommend, no_action]`. Highlighted nodes get a CSS class. Node names mirror the vendored graph, and no tracing endpoint is added.

7. **Formatting.** Propensity shows 4 significant decimals labeled "raw score". Money values show 2 decimals followed by the country, since amounts are in local currency. Integers use thousands separators. `null` renders as a muted dash. Presets are buttons with a small behavior badge (ACTION or NO CONSENT). The loaded decision badge comes from the API response.

8. **Lightweight tests.** `tests/ui/test_ui.py` uses TestClient with dependency overrides and no lifespan. `GET /` returns 200 HTML referencing `/static/app.js` and `/static/styles.css`; both assets return 200; the HTML, JS, and CSS contain no `http://` or `https://` references; every API path literal in `app.js` matches the four allowed endpoint patterns; `/` is absent from the OpenAPI schema. No JS test runner. Behavior is checked with the README manual checklist.

## Risks / Trade-offs

- [UI logic has no automated behavior tests] → The JS is kept small and centralized (one client, one render per panel). A manual checklist covers every spec scenario on real artifacts.
- [Presets could drift if the artifacts change] → Labels are hints only, and the page always shows the API decision. The checklist re-verifies the presets.
- [The NEGATIVE_VALUE and NO_SUPPORTED paths aren't visible in the live demo] → Real data doesn't produce them. They stay covered by backend tests. The README notes this so presenters don't promise them.
- [Serving the UI at `/` adds a public route] → The route is static and read-only, has no data, and is excluded from OpenAPI.

## Migration Plan

Additive: static files plus two lines of wiring. Rebuild the image and open `http://127.0.0.1:8000/`. Rollback means reverting the change's commits.
