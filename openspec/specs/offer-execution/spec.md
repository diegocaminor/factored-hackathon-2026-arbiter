# offer-execution Specification

## Purpose

Act on a next best action recommendation, either by simulating delivery of the recommended offer to the customer or by escalating the customer to a human queue, with deterministic responses and no external providers.

## Requirements

### Requirement: Confirm an actionable recommendation
The service SHALL respond to `POST /customers/{customer_id}/confirm` for a known customer whose current recommendation is `ACTION` with HTTP 200. It SHALL simulate sending the recommended offer and return a JSON object with `status` equal to `SIMULATED_SENT`, `customer_id`, and the `product`, `channel`, and `provider_message_id` of the simulated send. The product and channel SHALL be those of the customer's current recommendation, which the service computes itself; it SHALL NOT require a request body.

#### Scenario: Customer with an ACTION recommendation confirms
- **WHEN** a client sends `POST /customers/{customer_id}/confirm` for a known customer whose next best action decision is `ACTION`
- **THEN** the response has HTTP 200, `status` equal to `SIMULATED_SENT`, `customer_id` equal to the requested ID, and `product` and `channel` equal to those returned by `GET /customers/{customer_id}/next-best-action`

### Requirement: Confirmation requires an ACTION decision
The service SHALL respond to `POST /customers/{customer_id}/confirm` with HTTP 409 and a JSON `detail` message naming the current decision when the known customer's current decision is not `ACTION`. It SHALL NOT simulate a send in that case.

#### Scenario: Customer without marketing consent confirms
- **WHEN** a client sends `POST /customers/{customer_id}/confirm` for a known customer whose decision is `NO_ACTION_CONSENT`
- **THEN** the response has HTTP 409 and a `detail` message containing `NO_ACTION_CONSENT`, and no send is simulated

#### Scenario: Any non-ACTION decision is rejected
- **WHEN** a client confirms for a known customer whose decision is `NO_ACTION_NO_SUPPORTED_CANDIDATES` or `NO_ACTION_NEGATIVE_VALUE`
- **THEN** the response has HTTP 409 and a `detail` message containing that decision

### Requirement: Unknown customer on execution endpoints
The service SHALL respond with HTTP 404 and a JSON `detail` message naming the missing customer when `POST /customers/{customer_id}/confirm` or `POST /customers/{customer_id}/handoff` targets a customer that is not in the customer snapshot. It SHALL NOT simulate a send or create a handoff in that case.

#### Scenario: Confirm for an unknown customer
- **WHEN** a client sends `POST /customers/{customer_id}/confirm` for an ID that is not in the customer snapshot
- **THEN** the response has HTTP 404 and a `detail` message naming the missing customer

#### Scenario: Handoff for an unknown customer
- **WHEN** a client sends `POST /customers/{customer_id}/handoff` for an ID that is not in the customer snapshot
- **THEN** the response has HTTP 404 and a `detail` message naming the missing customer

### Requirement: Deterministic simulated delivery
A simulated send SHALL NOT contact any external system or provider. Its `provider_message_id` SHALL be `demo-{customer_id}-{channel}` with every space replaced by a hyphen, so identical inputs always produce the same identifier.

#### Scenario: Provider message identifier format
- **WHEN** a known customer `CLI-X` whose recommendation uses channel `Push` confirms
- **THEN** `provider_message_id` equals `demo-CLI-X-Push`

### Requirement: Simulated human handoff
The service SHALL respond to `POST /customers/{customer_id}/handoff` for any known customer, regardless of the current decision, with HTTP 200 and a JSON object with `status` equal to `HANDOFF_CREATED`, `customer_id`, `reason`, and `queue` equal to `sales-assistance`. Creating a handoff SHALL NOT contact any external system.

#### Scenario: Handoff for a known customer
- **WHEN** a client sends `POST /customers/{customer_id}/handoff` for a known customer
- **THEN** the response has HTTP 200, `status` equal to `HANDOFF_CREATED`, `customer_id` equal to the requested ID, and `queue` equal to `sales-assistance`

#### Scenario: Handoff for a customer with a NO_ACTION decision
- **WHEN** a client requests a handoff for a known customer whose decision is `NO_ACTION_CONSENT`
- **THEN** the response has HTTP 200 and `status` equal to `HANDOFF_CREATED`

### Requirement: Handoff reason
`POST /customers/{customer_id}/handoff` SHALL accept an optional JSON body with a `reason` field of type string or null. When the body is absent or `reason` is absent or null, the response `reason` SHALL be `Customer did not confirm automated execution.`. Otherwise it SHALL be the provided reason. A body that is not a JSON object, or a `reason` that is not a string or null, SHALL be rejected with HTTP 422.

#### Scenario: Default reason
- **WHEN** a client requests a handoff for a known customer without a body, or with `{"reason": null}`
- **THEN** the response `reason` equals `Customer did not confirm automated execution.`

#### Scenario: Custom reason
- **WHEN** a client requests a handoff for a known customer with `{"reason": "Customer asked for an advisor"}`
- **THEN** the response `reason` equals `Customer asked for an advisor`

#### Scenario: Invalid reason type
- **WHEN** a client requests a handoff with `{"reason": 123}`
- **THEN** the response has HTTP 422

### Requirement: Stateless execution
Confirm and handoff SHALL NOT persist any record of executions or handoffs. Repeated identical requests SHALL each be processed independently and return identical responses.

#### Scenario: Repeated confirmation
- **WHEN** a client confirms twice for the same known customer with an `ACTION` decision
- **THEN** both responses have HTTP 200 and identical bodies, including `provider_message_id`

### Requirement: Documented execution endpoints
The OpenAPI document SHALL describe `POST /customers/{customer_id}/confirm` with its 200 response schema and its 404 and 409 responses, and `POST /customers/{customer_id}/handoff` with its optional request body, its 200 response schema, and its 404 response.

#### Scenario: Swagger shows the execution endpoints
- **WHEN** a developer opens `/docs` or requests `/openapi.json`
- **THEN** both POST endpoints appear with their documented response schemas and error responses, and the handoff request body is marked optional
