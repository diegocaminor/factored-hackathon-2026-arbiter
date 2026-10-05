# Proposal

## Why

The API recommends a next best action but stops there. A demo of the banking workflow needs the step after the recommendation: either execute the recommended offer or escalate to a human. The vendored LangGraph agent already models these two outcomes (`simulate_offer_tool`, `handoff_to_human_tool`), but importing it pulls in LangGraph, which is out of scope. These outcomes should be exposed over HTTP now, deterministically and without external providers, so the demo and a future agent share the same contract.

## What Changes

- Add `POST /customers/{customer_id}/confirm`. It recomputes the customer's recommendation through the existing NBA service. If the decision is `ACTION`, it simulates sending the recommended offer and returns `status` (`SIMULATED_SENT`), `customer_id`, `product`, `channel`, and a deterministic `provider_message_id`.
- `confirm` returns 404 for unknown customers and 409 Conflict when the current decision is not `ACTION`. It takes no request body: the server's recommendation is the source of truth.
- Add `POST /customers/{customer_id}/handoff`. It creates a simulated human handoff and returns `status` (`HANDOFF_CREATED`), `customer_id`, `reason`, and `queue` (`sales-assistance`). It accepts an optional JSON body `{"reason": string | null}` and defaults the reason to "Customer did not confirm automated execution." Unknown customers get 404.
- Both endpoints return 200 OK on success, use Pydantic schemas, and are documented in Swagger, including their 404 and 409 responses.
- Response values (statuses, ID format, queue, default reason) match the vendored agent's tools, so a later LangGraph integration produces identical payloads.
- Execution is stateless. Repeated `confirm` calls simulate repeated sends and return the same `provider_message_id`.

Out of scope: real providers (Twilio, WhatsApp, SMS, Push) or any external system, persistence, idempotency, audit history, LangGraph integration, UI, and changes to the recommendation logic or the `next-best-action` contract.

## Capabilities

### New Capabilities

- `offer-execution`: Acting on a recommendation, either by simulating delivery of the recommended offer or by escalating the customer to a human queue, including the validation rules and response contracts for both.

### Modified Capabilities

None. `next-best-action` and `http-service` requirements stay the same. Only README examples change.

## Impact

- Code: a new `app/execution/` feature package (schemas, simulated adapters, service, router). `app/main.py` registers the router and builds the execution service on the existing `NBAService`. `src/propensity` and `app/nba/` behavior stay unchanged.
- APIs: two new POST endpoints; existing endpoints are unchanged.
- Dependencies: none added.
- Docs: README gains the two endpoints with example requests and responses.
- Tests: unit and router tests with the existing test fakes, and integration checks against real artifacts for an `ACTION` customer and a non-`ACTION` customer.
