# Tasks

## 1. Serving the UI

- [x] 1.1 Add `app/static/` with placeholder `index.html`, `app.js`, and `styles.css`. In `app/main.py`, mount `/static` (path resolved relative to the module) and add `GET /` returning `index.html` with `include_in_schema=False`. Verify with `tests/ui/test_ui.py`: `GET /` returns 200 HTML referencing `/static/app.js` and `/static/styles.css`, both assets return 200, `/` is absent from `/openapi.json`, and the existing test suite still passes.

## 2. Page

- [x] 2.1 Build `index.html` and `styles.css`: header with title and a `/docs` link, a customer bar (preset buttons with ACTION or NO CONSENT badges, free-text input, Load button), recommendation card, candidates table, actions card (Confirm with a disabled hint, Handoff with an optional reason), execution result panel, agent panel (`user_confirmed` toggle, Run button, node path, status and message), and an error banner. Verify the page renders in a browser against a running server and that the files contain no external URLs (test assertion).
- [x] 2.2 Implement `app.js`: a single `api()` client with typed results (OK, HTTP error with `detail`, connection error); load via `GET /customers/{id}/next-best-action?include_candidates=true` with formatting (raw propensity, money with country, thousands separators, a dash for null); Confirm enabled only for `ACTION`; Handoff with an optional reason body; agent run via `POST /agent/run` with the status-to-path map; the error banner for 404, 409, 422, and connection errors; result panels reset when a new customer loads. Verify with the test assertion that every API path literal in `app.js` matches only the four existing endpoints and that no external URL appears.

## 3. Docs and demo verification

- [ ] 3.1 Update README with the UI URL (`http://127.0.0.1:8000/`), what each panel does, the preset list with the note that labels are hints and the API decides, the note that only ACTION and NO CONSENT occur in real data, and a manual demo checklist covering every `demo-ui` scenario. Verify by running the checklist end to end in a browser against the Docker image with mounted artifacts: ACTION preset load and candidates, Confirm, Handoff with and without a reason, Confirm disabled for NO CONSENT, agent COMPLETED, HANDOFF, and NO_ACTION paths, unknown-ID 404 banner, and the connection-error banner after stopping the container.

## 4. Integration and scope checks

- [ ] 4.1 Review the final diff: only `app/static/*`, `app/main.py` (mount plus `GET /`), tests, and README changed; no new dependency, endpoint (beyond `GET /`), Dockerfile, or `.dockerignore` change; no ML import or artifact path in the static files. Run the full test suite and `openspec validate add-demo-ui --strict`.
