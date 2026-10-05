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
After installing the documented dependencies and placing the NBA artifacts under the artifacts directory, a developer SHALL be able to start the service from the repository root using the documented development command, which runs `uvicorn app.main:app --reload` with `src` on the Python import path, and access it at `http://127.0.0.1:8000`.

#### Scenario: Local startup
- **WHEN** a developer runs the documented local command with port 8000 available and artifacts present in `./artifacts/propensity`
- **THEN** the service starts with development reload enabled and serves `/health`, `/docs`, `/openapi.json`, and the next-best-action endpoint

### Requirement: Container execution
With Docker available, a developer SHALL be able to build using `docker build -t factored-nba .` and run using `docker run -p 8000:8000` with the host artifacts directory mounted read-only at the container's `ARTIFACTS_DIR`. The container SHALL run as a non-root user without development reload and expose the same HTTP behavior through host port 8000.

#### Scenario: Build and run the container
- **WHEN** a developer executes the documented build command, then the documented run command with the artifacts mounted and port 8000 available
- **THEN** the container serves `/health`, `/docs`, `/openapi.json`, and the next-best-action endpoint at `http://127.0.0.1:8000`, runs with a nonzero user ID, and does not enable reload

### Requirement: Configurable artifact location
The service SHALL resolve NBA artifacts from the directory named by the `ARTIFACTS_DIR` environment variable. When the variable is unset, it SHALL use `./artifacts/propensity` relative to the working directory. The service SHALL NOT depend on Google Drive or any remote storage at runtime.

#### Scenario: Default artifact directory
- **WHEN** the service starts from the repository root without `ARTIFACTS_DIR` set and artifacts are present in `./artifacts/propensity`
- **THEN** startup succeeds using those artifacts

#### Scenario: Overridden artifact directory
- **WHEN** the service starts with `ARTIFACTS_DIR` pointing to another directory that contains the artifacts
- **THEN** startup succeeds using the artifacts from that directory

### Requirement: Fail-fast artifact loading
The service SHALL load the model, action catalog, customer snapshot, and NBA metadata once during startup, before accepting requests, and SHALL reuse them for every request. If any required artifact is missing or cannot be loaded, startup SHALL fail with an error that names the artifact path, and the service SHALL NOT serve requests. `GET /health` SHALL continue to report liveness only.

#### Scenario: Missing artifact
- **WHEN** the service starts and the customer snapshot file is absent from the artifacts directory
- **THEN** the process exits during startup with an error naming the missing file path, and no port serves requests

#### Scenario: Artifacts reused across requests
- **WHEN** the running service handles multiple next-best-action requests
- **THEN** no artifact file is read again after startup

### Requirement: Container image contents
The container image SHALL contain the application source and the `propensity` package source. It SHALL exclude NBA artifacts, notebooks, secrets, Git metadata, and development caches. Artifacts SHALL be provided at run time through a mount.

#### Scenario: Image excludes artifacts and research files
- **WHEN** the image is built from the repository with artifacts present on the host
- **THEN** the image's application directory contains `app/` and `src/propensity/` sources, and no model, parquet, notebook, environment, or Git files
