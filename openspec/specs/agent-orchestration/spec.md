# agent-orchestration Specification

## Purpose

Run the existing NBA workflow graph (load customer, recommend, route, confirmation gate, simulated execution, human handoff) over HTTP as a stateless single request, with the propensity model and NBA engine as the only source of recommendation values.

## Requirements

### Requirement: Agent run endpoint
The service SHALL accept `POST /agent/run` with a JSON object containing `customer_id` (string) and `user_confirmed` (JSON boolean), both required. For a known customer it SHALL run the NBA workflow graph once and respond with HTTP 200 and a JSON object containing `customer_id`, `user_confirmed`, `status`, `recommendation`, `consent_required`, `product_details`, `execution_result`, and `assistant_message`.

#### Scenario: Known customer runs the workflow
- **WHEN** a client sends `POST /agent/run` with a known `customer_id` and a boolean `user_confirmed`
- **THEN** the response has HTTP 200, `customer_id` equal to the requested ID, `user_confirmed` equal to the requested value, and a `recommendation` object with `decision`, `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support`

### Requirement: Confirmed ACTION executes the simulated offer
When the customer's decision is `ACTION` and `user_confirmed` is `true`, the workflow SHALL simulate sending the recommended offer and finish with `status` `COMPLETED`. `execution_result` SHALL contain `status` `SIMULATED_SENT`, `customer_id`, `product`, `channel`, and `provider_message_id`.

#### Scenario: Customer confirms an ACTION recommendation
- **WHEN** a client runs the agent for a known customer with an `ACTION` decision and `user_confirmed=true`
- **THEN** `status` is `COMPLETED`, `consent_required` is `true`, and `execution_result.status` is `SIMULATED_SENT` with the recommended product and channel

### Requirement: Unconfirmed ACTION creates a human handoff
When the customer's decision is `ACTION` and `user_confirmed` is `false`, the workflow SHALL NOT simulate a send. It SHALL create a simulated human handoff and finish with `status` `HANDOFF`. `execution_result` SHALL contain `status` `HANDOFF_CREATED`, `customer_id`, `reason` `Customer did not confirm automated execution.`, and `queue` `sales-assistance`.

#### Scenario: Customer declines an ACTION recommendation
- **WHEN** a client runs the agent for a known customer with an `ACTION` decision and `user_confirmed=false`
- **THEN** `status` is `HANDOFF`, `execution_result.status` is `HANDOFF_CREATED`, and no offer send is simulated

### Requirement: NO_ACTION decisions end without execution
When the customer's decision is any `NO_ACTION_*` value, the workflow SHALL end without simulating a send or creating a handoff, regardless of `user_confirmed`. `status` SHALL equal the decision, `execution_result` SHALL be `null`, and `assistant_message` SHALL name the decision.

#### Scenario: Customer without marketing consent
- **WHEN** a client runs the agent for a known customer whose decision is `NO_ACTION_CONSENT`, with `user_confirmed` either `true` or `false`
- **THEN** the response has HTTP 200, `status` `NO_ACTION_CONSENT`, `execution_result` `null`, and recommendation economic fields `null`

### Requirement: Unknown customer
The service SHALL respond with HTTP 404 and a JSON `detail` message naming the missing customer when `customer_id` is not in the customer snapshot. It SHALL NOT invoke the workflow graph in that case.

#### Scenario: Agent run for an unknown customer
- **WHEN** a client sends `POST /agent/run` with a `customer_id` that is not in the customer snapshot
- **THEN** the response has HTTP 404 and a `detail` message naming the missing customer, and the graph is not invoked

### Requirement: Request validation
The service SHALL respond with HTTP 422 when the body is missing, is not a JSON object, lacks `customer_id` or `user_confirmed`, or has a `user_confirmed` that is not a JSON boolean. Strings such as `"true"` and numbers such as `1` SHALL be rejected, so no default ever triggers a handoff.

#### Scenario: Missing confirmation flag
- **WHEN** a client sends `POST /agent/run` with only `customer_id`
- **THEN** the response has HTTP 422 and the graph is not invoked

#### Scenario: Non-boolean confirmation flag
- **WHEN** a client sends `user_confirmed` as `"true"` or `1`
- **THEN** the response has HTTP 422

### Requirement: Engine is the source of truth
The workflow SHALL obtain the recommendation only from the NBA engine through the existing graph. No component SHALL generate, alter, or override product, channel, propensity, or economic values. The `recommendation` returned by `POST /agent/run` SHALL equal the corresponding fields of `GET /customers/{customer_id}/next-best-action` for the same customer.

#### Scenario: Agent matches the NBA endpoint
- **WHEN** the agent runs for a known customer and `GET /customers/{customer_id}/next-best-action` is requested for the same customer
- **THEN** `decision`, `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support` are equal

### Requirement: Execution parity with execution endpoints
The `execution_result` produced by the workflow SHALL equal the response body of the corresponding execution endpoint for the same customer: `POST /customers/{customer_id}/confirm` for a confirmed ACTION, and `POST /customers/{customer_id}/handoff` without a body for an unconfirmed ACTION.

#### Scenario: Confirmed run matches confirm
- **WHEN** the agent runs with `user_confirmed=true` for a customer with an `ACTION` decision
- **THEN** `execution_result` equals the body of `POST /customers/{customer_id}/confirm` for that customer

#### Scenario: Unconfirmed run matches handoff
- **WHEN** the agent runs with `user_confirmed=false` for a customer with an `ACTION` decision
- **THEN** `execution_result` equals the body of `POST /customers/{customer_id}/handoff` without a body for that customer

### Requirement: Single source of truth for minimum historical support
The workflow SHALL apply the minimum historical sends threshold loaded from the NBA metadata, the same value the NBA endpoint uses. No fallback or duplicated threshold SHALL exist in the workflow integration. Startup SHALL fail with an error naming the metadata file when `min_historical_sends` is absent or is not a positive integer.

#### Scenario: Invalid threshold in metadata
- **WHEN** the service starts with an NBA metadata file whose `min_historical_sends` is `0`, negative, a boolean, or not an integer
- **THEN** startup fails with an error naming the metadata file and the invalid key

#### Scenario: Threshold flows from metadata to the workflow
- **WHEN** the metadata threshold is set above a catalog action's historical sends and the agent runs for a customer in that action's country
- **THEN** neither the workflow's recommendation nor the NBA endpoint's recommendation selects that action

### Requirement: Stateless orchestration
Each `POST /agent/run` SHALL run the workflow to completion within the request. The service SHALL NOT persist graph state, use a checkpointer, or require a thread identifier. Repeated identical requests SHALL return identical responses.

#### Scenario: Repeated run
- **WHEN** a client sends the same `POST /agent/run` request twice
- **THEN** both responses have HTTP 200 and identical bodies

### Requirement: Safe response contract
The response SHALL contain only JSON-safe values and SHALL NOT include the customer's raw snapshot row, ranked catalog rows, or internal catalog columns.

#### Scenario: Internal state is not exposed
- **WHEN** any agent run response is serialized
- **THEN** it parses with a strict JSON parser that rejects NaN and infinity, and contains no `customer_row` or `ranked_actions` field

### Requirement: Documented agent endpoint
The OpenAPI document SHALL describe `POST /agent/run` with its required request body, its HTTP 200 response schema, and its HTTP 404 response.

#### Scenario: Swagger shows the agent endpoint
- **WHEN** a developer opens `/docs` or requests `/openapi.json`
- **THEN** `POST /agent/run` appears with a required request body containing `customer_id` and `user_confirmed`, a 200 response schema, and a documented 404 response
