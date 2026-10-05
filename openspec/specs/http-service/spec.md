# http-service Specification

## Purpose

Provide a minimal HTTP entry point that developers can run locally or in a container before connecting the experimental decision pipeline.

## Requirements

### Requirement: HTTP liveness
The service SHALL respond to `GET /health` with HTTP 200 and a JSON object containing exactly `{"status": "ok"}`. This response SHALL report HTTP application liveness, not model readiness.

#### Scenario: Running service answers a health request
- **WHEN** a client sends `GET /health` to the running service
- **THEN** the response has HTTP status 200, a JSON content type, and exactly the object `{"status": "ok"}`

### Requirement: Discoverable API documentation
The service SHALL expose Swagger UI at `/docs` and an OpenAPI JSON document at `/openapi.json` describing `GET /health`.

#### Scenario: Developer explores the API
- **WHEN** a developer opens `/docs` in a browser
- **THEN** the service returns HTTP 200 and the Swagger UI displays `GET /health`

#### Scenario: Client reads the API contract
- **WHEN** a client requests `/openapi.json`
- **THEN** the service returns HTTP 200 and a valid OpenAPI JSON document containing a GET operation for `/health`

### Requirement: Local development execution
After installing the documented dependencies, a developer SHALL be able to start the service from the repository root with `uvicorn app.main:app --reload` and access it at `http://127.0.0.1:8000`.

#### Scenario: Local startup
- **WHEN** a developer runs the documented local command with port 8000 available
- **THEN** the service starts with development reload enabled and serves `/health`, `/docs`, and `/openapi.json`

### Requirement: Container execution
With Docker available, a developer SHALL be able to build using `docker build -t factored-nba .` and run using `docker run -p 8000:8000 factored-nba`. The container SHALL run as a non-root user without development reload and expose the same HTTP behavior through host port 8000.

#### Scenario: Build and run the container
- **WHEN** a developer executes the documented build and run commands with port 8000 available
- **THEN** the container serves `/health`, `/docs`, and `/openapi.json` at `http://127.0.0.1:8000`, runs with a nonzero user ID, and does not enable reload

### Requirement: Independent runtime
The service SHALL start without propensity modules, ML artifacts, LangGraph, or application credentials. Its container build context and runtime image SHALL exclude notebooks, ML source and artifacts, secrets, Git metadata, and development caches.

#### Scenario: Experimental resources are absent
- **WHEN** the service starts locally or in Docker without propensity code, model files, or credentials
- **THEN** startup succeeds and the health and documentation endpoints remain available without contacting an ML or agent service

#### Scenario: Container packaging excludes research resources
- **WHEN** the image is built from the repository
- **THEN** notebooks, ML source and artifacts, secrets, Git metadata, and development caches are excluded from the build context and absent from the application directory in the image
