# next-best-action Specification

## Purpose

Serve per-customer Next Best Action recommendations over HTTP from the frozen propensity model and the deterministic NBA engine, so clients can get the decision and its economics without running notebooks.

## Requirements

### Requirement: Recommendation for a known customer
The service SHALL respond to `GET /customers/{customer_id}/next-best-action` for a customer present in the customer snapshot with HTTP 200 and a JSON object containing `customer_id`, `country`, `decision`, `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support`.

#### Scenario: Customer with a recommended action
- **WHEN** a client requests the next best action for a known, marketing-eligible customer whose best candidate has positive expected value
- **THEN** the response has HTTP 200, `decision` equal to `ACTION`, non-null `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support`, and `customer_id` equal to the requested ID

#### Scenario: Country is reported with economic values
- **WHEN** a client requests the next best action for any known customer
- **THEN** the response includes the customer's `country`, which identifies the local currency of the economic fields

### Requirement: Unknown customer
The service SHALL respond with HTTP 404 and a JSON error body when `customer_id` is not present in the customer snapshot. It SHALL NOT invoke the model for unknown customers.

#### Scenario: Customer does not exist
- **WHEN** a client requests the next best action for an ID that is not in the customer snapshot
- **THEN** the response has HTTP 404 and a JSON body with a `detail` message naming the missing customer

### Requirement: Decision vocabulary
The `decision` field SHALL be one of `ACTION`, `NO_ACTION_CONSENT`, `NO_ACTION_NO_SUPPORTED_CANDIDATES`, or `NO_ACTION_NEGATIVE_VALUE`. Every decision for a known customer SHALL return HTTP 200. Fields the engine does not provide for a decision SHALL be `null`.

#### Scenario: Customer without marketing consent
- **WHEN** a client requests the next best action for a known customer who does not accept marketing
- **THEN** the response has HTTP 200, `decision` equal to `NO_ACTION_CONSENT`, and `null` for `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support`

#### Scenario: Best candidate has non-positive expected value
- **WHEN** the engine's top-ranked candidate for a known customer has expected value less than or equal to zero
- **THEN** the response has HTTP 200, `decision` equal to `NO_ACTION_NEGATIVE_VALUE`, and the product, channel, and economic fields of that top candidate

#### Scenario: No supported candidates
- **WHEN** a known, consenting customer's country has no catalog action meeting the minimum historical support
- **THEN** the response has HTTP 200, `decision` equal to `NO_ACTION_NO_SUPPORTED_CANDIDATES`, and `null` product, channel, and economic fields

### Requirement: Optional ranked candidates
The endpoint SHALL accept an optional boolean query parameter `include_candidates`, defaulting to `false`. When it is `true`, the response SHALL include `candidates`: up to five scored actions ordered by ascending rank, each with `rank`, `product`, `channel`, `propensity`, `expected_conversion_value`, `estimated_send_cost`, `expected_value`, and `historical_support`. When it is `false`, `candidates` SHALL be `null`.

#### Scenario: Candidates requested
- **WHEN** a client requests the next best action for a known customer with `include_candidates=true` and the engine scored at least one action
- **THEN** `candidates` contains at most five entries, ranks are strictly increasing starting at 1, and the first entry matches the top-level recommendation when `decision` is `ACTION`

#### Scenario: Candidates not requested
- **WHEN** a client requests the next best action without `include_candidates`
- **THEN** `candidates` is `null`

#### Scenario: Candidates requested but none scored
- **WHEN** a client requests candidates for a known customer whose decision is `NO_ACTION_CONSENT` or `NO_ACTION_NO_SUPPORTED_CANDIDATES`
- **THEN** `candidates` is an empty list

### Requirement: Engine fidelity
The recommendation SHALL equal the output of the existing `recommend_next_best_action()` for the customer's snapshot row. It SHALL use the frozen model, the pre-test action catalog, and the model features, categorical features, and minimum historical sends recorded in the NBA metadata. The service SHALL NOT retrain, re-tune, or recalibrate the model, and it SHALL NOT read final-test artifacts.

#### Scenario: API matches the engine
- **WHEN** the recommendation for a known customer is computed both by calling `recommend_next_best_action()` directly with the same artifacts and metadata and through the endpoint
- **THEN** the decision, product, channel, and numeric fields are equal

#### Scenario: Propensity is the raw model score
- **WHEN** a client reads `propensity` from any response
- **THEN** the value is the uncalibrated model score used by the engine, and the API documentation describes it as raw

### Requirement: JSON-safe response contract
All response fields SHALL serialize as standard JSON strings, numbers, booleans, `null`, arrays, or objects. NaN and infinity SHALL NOT appear in responses.

#### Scenario: Numeric values serialize cleanly
- **WHEN** any next-best-action response is serialized
- **THEN** it parses with a strict JSON parser that rejects NaN and infinity

### Requirement: Documented endpoint
The OpenAPI document SHALL describe `GET /customers/{customer_id}/next-best-action` with its path parameter, its `include_candidates` query parameter, its HTTP 200 response schema, and its HTTP 404 response.

#### Scenario: Swagger shows the endpoint
- **WHEN** a developer opens `/docs` or requests `/openapi.json`
- **THEN** the endpoint appears with both parameters, a 200 response schema containing the recommendation fields, and a documented 404 response
