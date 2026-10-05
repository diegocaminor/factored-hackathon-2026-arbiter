# demo-ui Specification

## Purpose

Provide a single browser page, served by the service itself, that demonstrates the Next Best Action recommendation, offer confirmation, human handoff, and the LangGraph workflow using only the existing HTTP API.

## Requirements

### Requirement: UI is served by the service
The service SHALL respond to `GET /` with HTTP 200 and an HTML page, and SHALL serve the page's JavaScript and CSS under `/static/`. The page SHALL load without any build step, external CDN, or additional server process, and SHALL link to `/docs` from its header.

#### Scenario: Developer opens the demo
- **WHEN** a browser requests `http://127.0.0.1:8000/` from a running service
- **THEN** the response has HTTP 200 with an HTML content type, and the page's script and stylesheet load from `/static/` with HTTP 200

#### Scenario: No external assets
- **WHEN** the served HTML, JavaScript, and CSS are inspected
- **THEN** they reference no external host and only same-origin paths

### Requirement: API-only data access
The UI SHALL obtain all data by calling only `GET /customers/{customer_id}/next-best-action`, `POST /customers/{customer_id}/confirm`, `POST /customers/{customer_id}/handoff`, and `POST /agent/run`. Serving the UI SHALL NOT add any backend endpoint for customer discovery, graph tracing, or observability. The UI SHALL NOT import ML modules or read artifacts.

#### Scenario: Only existing endpoints are referenced
- **WHEN** the UI's JavaScript is inspected
- **THEN** every API path it calls is one of the four endpoints listed above

### Requirement: Customer selection
The page SHALL offer demo presets `CLI-P21780PQ8D9W` and `CLI-S5RL0QD6GG1U` labeled ACTION, and `CLI-P8F6JG7TN8YN` and `CLI-QHXK2HCRNFBI` labeled NO CONSENT, plus a free-text input that accepts any customer ID. Preset labels SHALL be hints only. The decision shown SHALL always be the one returned by the API.

#### Scenario: Selecting a preset
- **WHEN** the user selects a preset
- **THEN** its customer ID fills the input and the recommendation is loaded from the API

#### Scenario: Entering an arbitrary customer ID
- **WHEN** the user types any customer ID and loads it
- **THEN** the page requests that ID from the API and shows the API's decision, whatever the preset labels say

### Requirement: Recommendation display
After loading a customer, the page SHALL display the decision, country, product, channel, propensity labeled as a raw score, expected value, and historical support from the NBA endpoint, and a table of up to five candidate actions (rank, product, channel, propensity, expected value, historical support) requested with `include_candidates=true`. Missing values SHALL be shown as a placeholder rather than blank or `null` text.

#### Scenario: ACTION customer
- **WHEN** the user loads `CLI-P21780PQ8D9W`
- **THEN** the card shows decision `ACTION`, product `Tarjeta Crédito`, channel `Push`, and the numeric fields, and the candidates table shows up to five ranked rows

#### Scenario: NO CONSENT customer
- **WHEN** the user loads `CLI-P8F6JG7TN8YN`
- **THEN** the card shows decision `NO_ACTION_CONSENT` with placeholder values and an empty candidates state

### Requirement: Confirm action
The page SHALL provide a Confirm button that calls `POST /customers/{customer_id}/confirm` for the loaded customer. The button SHALL be enabled only when the loaded decision is `ACTION`, and otherwise disabled with a visible explanation.

#### Scenario: Confirming an ACTION customer
- **WHEN** an ACTION customer is loaded and the user clicks Confirm
- **THEN** the page calls the confirm endpoint and shows the returned `status`, product, channel, and `provider_message_id`

#### Scenario: Confirm unavailable
- **WHEN** a customer whose decision is not `ACTION` is loaded
- **THEN** the Confirm button is disabled and the page states that only ACTION recommendations can be confirmed

### Requirement: Handoff action
The page SHALL provide a Handoff button with an optional reason field. It SHALL call `POST /customers/{customer_id}/handoff`, sending `{"reason": <text>}` when a reason is entered and no reason otherwise, and SHALL show the returned `status`, `reason`, and `queue`.

#### Scenario: Handoff without reason
- **WHEN** the user clicks Handoff with an empty reason field
- **THEN** the page shows `HANDOFF_CREATED` with the default reason returned by the API

#### Scenario: Handoff with reason
- **WHEN** the user enters a reason and clicks Handoff
- **THEN** the page shows `HANDOFF_CREATED` with the entered reason

### Requirement: Agent workflow panel
The page SHALL provide a panel with a `user_confirmed` toggle and a Run button that calls `POST /agent/run` for the loaded customer. It SHALL display the response `status`, `assistant_message`, and `execution_result`, and SHALL highlight the workflow path derived only from the response `status`: load customer, recommend, prepare offer, execute offer for `COMPLETED`; load customer, recommend, prepare offer, handoff for `HANDOFF`; and load customer, recommend, no action for any `NO_ACTION_*` status.

#### Scenario: Confirmed agent run
- **WHEN** an ACTION customer is loaded, the toggle is on, and the user runs the agent
- **THEN** the panel shows status `COMPLETED` and highlights the path ending in execute offer

#### Scenario: Unconfirmed agent run
- **WHEN** an ACTION customer is loaded, the toggle is off, and the user runs the agent
- **THEN** the panel shows status `HANDOFF` and highlights the path ending in handoff

#### Scenario: NO_ACTION agent run
- **WHEN** a NO CONSENT customer is loaded and the user runs the agent
- **THEN** the panel shows status `NO_ACTION_CONSENT` and highlights the path ending in no action

### Requirement: Visible errors
The page SHALL show a visible message, rather than failing silently, when the API returns 404, 409, or 422, or when the request cannot reach the server. The message SHALL include the API's `detail` text when one is returned.

#### Scenario: Unknown customer
- **WHEN** the user loads a customer ID that does not exist
- **THEN** the page shows a not-found message containing the API's `detail`

#### Scenario: Server unreachable
- **WHEN** the API cannot be reached
- **THEN** the page shows a connection error message
