# Tasks

## 1. Minimal local service

- [ ] 1.1 Add `requirements.txt` with exact compatible FastAPI and plain Uvicorn pins, an empty `app/__init__.py`, and `app/main.py` with the application and health route; verify a clean Python 3.12 virtual environment installs with `python -m pip install -r requirements.txt`, passes `python -m pip check`, and contains no added ML or agent dependencies.
- [ ] 1.2 Start from the repository root using `uvicorn app.main:app --reload`; verify `curl -i http://127.0.0.1:8000/health` returns HTTP 200 with JSON content type and exactly `{"status":"ok"}`, `curl -f http://127.0.0.1:8000/docs` succeeds, and `curl -fsS http://127.0.0.1:8000/openapi.json | python -c 'import json,sys; assert "get" in json.load(sys.stdin)["paths"]["/health"]'` passes. Open `/docs` in a browser and confirm Swagger displays the health operation; verify editing/saving the app triggers development reload.
- [ ] 1.3 Append local setup, virtual-environment activation, startup, endpoint URLs, and the preceding smoke checks to README without replacing existing project content; verify those instructions work as written and describe health as liveness only and Swagger's default external asset requirement.

## 2. Container packaging

- [ ] 2.1 Add a single-stage Python 3.12 slim Dockerfile with requirements installed before copying `app/`, a dedicated non-root runtime user, and exec-form Uvicorn bound to `0.0.0.0:8000` without reload; inspect the Dockerfile for these properties. Defer the first build until the build-context exclusions in 2.2 are present.
- [ ] 2.2 Add an allowlisted `.dockerignore` permitting only Docker build inputs and app source, with secret and cache exclusions inside the permitted app tree; verify the rules exclude notebooks, propensity code, artifacts, environment files, private keys, Git, and tooling caches without reading secrets. Then verify `docker build -t factored-nba .` succeeds, inspect image configuration for the non-root user and startup command, and inspect the image's application directory with `docker run --rm --entrypoint sh factored-nba -c 'id -u; find . -type f'` to confirm a nonzero UID and only intended application inputs.
- [ ] 2.3 Stop the local server and execute `docker run -p 8000:8000 factored-nba`; repeat the health, docs, OpenAPI, and Swagger browser checks from 1.2 against host port 8000. Verify startup logs show one serving process and no reloader; stop the container after checks.
- [ ] 2.4 Add the exact Docker build/run commands and verification instructions to README; verify following them requires no Compose file, host ML dependencies, mounted artifacts, or application credentials.

## 3. Isolation and scope checks

- [ ] 3.1 Confirm both verified runtime modes start without `src/propensity`, artifacts, LangGraph, or credentials; inspect app imports, requirements, and startup behavior for no ML/agent initialization or external-service calls. If experimental resources have since arrived, repeat checks from an isolated temporary copy of only the documented runtime inputs rather than deleting or moving user files.
- [ ] 3.2 Review the final diff and smoke-check results against `specs/http-service/spec.md`; confirm only the planned app/package files and README changed during implementation, no notebooks or experimental resources were modified, and no UI or integration work was introduced.
