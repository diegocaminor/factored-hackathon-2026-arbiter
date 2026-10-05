# Design

## Context

See `proposal.md` for motivation and `specs/http-service/spec.md` for behavior. The repository currently contains nine root-level notebooks and a project README, but no application or dependency manifest. The existing propensity package and artifacts discussed by the user are not in this checkout; this scaffold does not require them. OpenSpec uses `spec-driven` with no additional project rules.

## Goals / Non-Goals

**Goals:** One importable application module, identical health behavior locally and in Docker, and explicit isolation from experimental assets.

**Non-Goals:** No notebook relocation, ML or LangGraph dependencies, UI, database, authentication, CORS, settings framework, service/repository layers, or separate routers. `/health` is liveness only.

## Decisions

1. **Keep the application in two files.** `app/__init__.py` is empty; `app/main.py` owns the FastAPI instance named `app` and the health route. Preserve default documentation endpoints. Separate routers and service layers would add indirection without a second capability; introduce them only when needed.
2. **Use one minimal dependency manifest.** `requirements.txt` contains exact, implementation-tested pins for FastAPI and plain Uvicorn. Use Python 3.12 locally and the matching official slim image as the initial baseline. Verify compatible available versions during implementation rather than claiming untested pins now. Do not install notebook dependencies or Uvicorn extras for this scaffold. A lockfile/tool migration is deferred.
3. **Use a single-stage container.** Set a working directory, copy and install requirements first for caching, then copy only `app/`. Run as a dedicated non-root user with exec-form Uvicorn startup, one process, and `--host 0.0.0.0 --port 8000`, without `--reload`. No Compose, Gunicorn, multi-stage build, or container health-check dependency is warranted.
4. **Prefer an allowlisted build context.** `.dockerignore` excludes everything except the Dockerfile, requirements, and the application source, with explicit secret/cache exclusions inside the allowed app tree. This protects notebooks, `src/propensity`, artifacts, environment files, keys, Git, and agent tooling metadata without needing their current locations. Explicit Docker COPY instructions provide a second boundary.
5. **Keep verification lightweight and reproducible.** Document smoke commands in README; use curl and Python's standard library for status/JSON/schema checks, and a browser for Swagger UI rendering. Execute the same checks against local and container startup. Do not add a testing framework solely for this scaffold.

## Risks / Trade-offs

- Direct dependency pins are not a full transitive lock → Verify a fresh installation and Docker build; defer a lockfile until dependency growth warrants it.
- Default Swagger UI assets need browser access to their CDN → Record this default behavior; offline documentation hosting is not part of this change.
- A healthy response does not imply model readiness → State the liveness-only contract in README; do not inspect model files.
- Future runtime files will be excluded by the allowlist → Update both COPY instructions and the allowlist deliberately when integrations are approved.

## Migration Plan

Add the application and packaging files without moving existing files; append setup and verification instructions to README. Verify locally first, then build and run the container using the exact requested commands. No data migration is involved. Rollback removes only these additions and the associated README section; notebooks and experimental resources remain untouched.
