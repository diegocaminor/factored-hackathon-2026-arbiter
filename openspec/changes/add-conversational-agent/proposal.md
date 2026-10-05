# Proposal

## Why

The service can recommend, confirm, and hand off, but only through structured endpoints a customer would never use directly. A customer-facing conversational agent shows the full Next Best Action flow in natural language, while keeping consequential actions behind deterministic application code and explicit customer intent rather than giving a language model the authority to execute them.

## What Changes

- Add `POST /agent/chat`: a stateless chat turn. The client sends `customer_id` and the conversation history on every request; the service returns the assistant reply, the classified intent, and the action taken, if any.
- An LLM classifies the intent of the customer's latest message into a fixed set: request recommendation, ask why the recommendation is relevant, ask about the product, confirm, decline, request human assistance, or unclear.
- Application code, not the LLM, dispatches the intent. It always recomputes the recommendation through the existing NBA service, enforces the confirmation gate, and executes confirm or handoff through the existing execution service.
- A second LLM call writes the customer-facing reply in the language of the customer's latest message, using only a customer-safe view of the facts: whether an offer exists, product, product summary, channel when needed, country when useful, and a safe execution outcome.
- Data minimization: the LLM never receives propensity, expected value, candidate rankings, historical support, customer model features (such as gender, marital status, income, or credit score), or implementation details (model family, decision engine, workflow framework).
- An output guard replaces any reply that mentions forbidden internal terms with a safe fallback message.
- Explanations stay generic and supported by available data. The agent never claims facts the service does not hold, such as recent interactions or currently owned products.
- For `NO_ACTION_CONSENT` and other non-actionable decisions, the agent presents no offer, replies neutrally, and offers human assistance.
- The LLM provider and model are configured through environment variables. When no provider is configured, `/agent/chat` responds with HTTP 503 and the rest of the application keeps working.

Out of scope: server-side conversation state, Redis, databases, LangGraph checkpointing, streaming responses, tool-use loops where the LLM calls execution functions directly, demo UI changes, and changes to `/agent/run`.

## Capabilities

### New Capabilities

- `conversational-agent`: Customer-facing chat turn over HTTP that interprets intent with an LLM, dispatches allowed workflows through deterministic application code, and replies in natural language using only customer-safe facts.

### Modified Capabilities

None. `next-best-action`, `offer-execution`, `agent-orchestration`, `http-service`, and `demo-ui` requirements are unchanged.

## Impact

- Code: new `app/chat/` package (router, schemas, service, chat model port with a provider adapter, safe-view builder, output guard). `app/main.py` registers the router and builds the chat service at startup only when a provider is configured.
- APIs: new `POST /agent/chat`. Existing endpoints are unchanged.
- Dependencies: the LLM provider SDK (`anthropic`) is added to `requirements.txt`.
- Configuration: new environment variables for the provider API key and model. The key is supplied at run time and never baked into the image.
- Tests: a fake chat model covers dispatch, confirmation gates, data minimization, forbidden-field absence, and output guard behavior without calling the real provider.
- Docs: README gains the chat endpoint, configuration, and examples.
