# Spec Delta

## Purpose

Let a customer talk to the bank in natural language about their next best offer, while an LLM only interprets intent and writes replies, deterministic application code decides and executes every action, and the NBA engine remains the source of truth for the recommendation.

## ADDED Requirements

### Requirement: Chat turn endpoint
The service SHALL accept `POST /agent/chat` with a JSON object containing `customer_id` (string) and `messages`, a non-empty list of `{role, content}` items where `role` is `user` or `assistant` and the last item has role `user`. For a known customer it SHALL respond with HTTP 200 and a JSON object containing `customer_id`, `reply`, `intent`, `action_taken`, and `execution_result`.

#### Scenario: Valid chat turn
- **WHEN** a client posts a known `customer_id` and a history whose last message is from the user
- **THEN** the response has HTTP 200 with `customer_id`, a non-empty `reply`, an `intent`, an `action_taken`, and an `execution_result` that is `null` when no action ran

### Requirement: Chat request validation
The service SHALL respond with HTTP 422 when the body is not a JSON object, lacks `customer_id` or `messages`, has an empty `messages` list, has a role other than `user` or `assistant`, has a last message whose role is not `user`, has more than 20 messages, or has a message `content` that is empty or longer than 2,000 characters.

#### Scenario: Last message is not from the user
- **WHEN** a client posts a history whose last message has role `assistant`
- **THEN** the response has HTTP 422 and no LLM call is made

#### Scenario: History too long
- **WHEN** a client posts 21 messages
- **THEN** the response has HTTP 422

### Requirement: Unknown customer
The service SHALL respond with HTTP 404 and a JSON `detail` naming the missing customer when `customer_id` is not in the customer snapshot. It SHALL NOT call the LLM in that case.

#### Scenario: Customer not found
- **WHEN** a client posts a `customer_id` that does not exist
- **THEN** the response has HTTP 404 with a `detail` naming that customer, and no LLM call is made

### Requirement: Provider not configured
When no LLM provider is configured, the service SHALL start normally and SHALL respond to `POST /agent/chat` with HTTP 503 and a JSON `detail` stating that the chat agent is unavailable. All other endpoints SHALL behave as they do with a provider configured.

#### Scenario: Chat without provider configuration
- **WHEN** the service runs without the provider environment variables and a client posts a valid chat request
- **THEN** the response has HTTP 503, and `GET /health` and `GET /customers/{customer_id}/next-best-action` still respond normally

### Requirement: Provider failure
If the LLM provider fails or returns an unusable result while classifying intent, the service SHALL respond with HTTP 502 and SHALL NOT execute any action. If it fails while writing the reply and no action ran, the service SHALL respond with HTTP 502. If it fails while writing the reply after an action already ran, the service SHALL still respond with HTTP 200, the real `action_taken` and `execution_result`, and a fixed fallback reply that describes the outcome.

#### Scenario: Classification fails
- **WHEN** the provider errors during intent classification
- **THEN** the response has HTTP 502 and no confirm or handoff is executed

#### Scenario: Reply writing fails without an action
- **WHEN** the intent is read-only and the provider errors while writing the reply
- **THEN** the response has HTTP 502

#### Scenario: Reply writing fails after a confirmation
- **WHEN** a confirm action has executed and the provider errors while writing the reply
- **THEN** the response has HTTP 200, `action_taken` `OFFER_CONFIRMED`, the confirm `execution_result`, and a fixed fallback reply

### Requirement: Intent set
The service SHALL classify the customer's latest message into exactly one of `REQUEST_RECOMMENDATION`, `ASK_WHY`, `ASK_PRODUCT`, `CONFIRM`, `DECLINE`, `REQUEST_HUMAN`, or `UNCLEAR`, and SHALL return it as `intent`. Earlier messages MAY inform interpretation, but consent SHALL come only from the latest user message.

#### Scenario: Off-topic message
- **WHEN** the latest message is unrelated to offers or assistance
- **THEN** `intent` is `UNCLEAR`

#### Scenario: Earlier consent is not reused
- **WHEN** an earlier user message said "yes, send it" and the latest user message asks what the product is
- **THEN** `intent` is `ASK_PRODUCT` and no confirm is executed

### Requirement: Engine is the source of truth
On every turn the service SHALL obtain the recommendation from the NBA engine for the given `customer_id`. No product, channel, decision, or economic value SHALL be taken from the conversation history or produced by the LLM, and the LLM SHALL NOT be able to change them.

#### Scenario: History claims a different product
- **WHEN** an assistant message in the history names a different product than the engine recommends
- **THEN** the reply and any execution use only the engine's product and channel

### Requirement: Read-only intents
For `REQUEST_RECOMMENDATION`, `ASK_WHY`, and `ASK_PRODUCT`, the service SHALL NOT execute any action. `action_taken` SHALL be `NONE` and `execution_result` SHALL be `null`.

#### Scenario: Asking for a recommendation
- **WHEN** an ACTION customer's latest message asks what is recommended
- **THEN** the reply presents the engine's product, `action_taken` is `NONE`, and nothing is sent or handed off

### Requirement: Confirmation gate
The service SHALL execute the offer confirmation only when the latest message's intent is `CONFIRM` and the engine decision is `ACTION`. It SHALL then return `action_taken` `OFFER_CONFIRMED` and an `execution_result` equal to the response of `POST /customers/{customer_id}/confirm`. Otherwise it SHALL NOT confirm, and SHALL reply with a clarifying message.

#### Scenario: Confirming an ACTION offer
- **WHEN** an ACTION customer's latest message clearly accepts the offer
- **THEN** `action_taken` is `OFFER_CONFIRMED` and `execution_result` has `status` `SIMULATED_SENT` with the engine's product and channel

#### Scenario: Confirming without an offer
- **WHEN** a `NO_ACTION_CONSENT` customer's latest message says "yes, send it"
- **THEN** no confirm is executed, `action_taken` is `NONE`, and the reply asks a clarifying question without presenting an offer

### Requirement: Decline
For `DECLINE`, the service SHALL NOT execute a confirm or create a handoff. `action_taken` SHALL be `NONE`, and the reply SHALL acknowledge the customer's choice and MAY offer human assistance.

#### Scenario: Customer declines
- **WHEN** an ACTION customer's latest message rejects the offer
- **THEN** `action_taken` is `NONE`, `execution_result` is `null`, and no handoff exists

### Requirement: Human assistance
For `REQUEST_HUMAN`, the service SHALL create a handoff for the customer with the fixed reason `Customer requested human assistance via chat.`, whatever the engine decision. It SHALL return `action_taken` `HANDOFF_CREATED` and an `execution_result` equal to the response of `POST /customers/{customer_id}/handoff` with that reason.

#### Scenario: Customer asks for an advisor
- **WHEN** the latest message asks to talk to a person
- **THEN** `action_taken` is `HANDOFF_CREATED` and `execution_result` has `status` `HANDOFF_CREATED`, the fixed reason, and queue `sales-assistance`

### Requirement: Non-actionable decisions
When the engine decision is not `ACTION`, the reply SHALL NOT present, name, or describe any product as an offer. It SHALL respond neutrally, SHALL NOT reveal the decision code or its reason, and SHALL offer human assistance.

#### Scenario: NO CONSENT customer asks for a recommendation
- **WHEN** a `NO_ACTION_CONSENT` customer asks what is recommended
- **THEN** the reply names no product, does not mention consent or decision codes, and offers to connect them with an advisor

### Requirement: Unclear intent
For `UNCLEAR`, the service SHALL execute no action and SHALL reply with a clarifying question about what the customer needs.

#### Scenario: Ambiguous message
- **WHEN** the latest message is "hmm, maybe"
- **THEN** `action_taken` is `NONE` and the reply asks the customer to clarify

### Requirement: Customer-safe view
The LLM SHALL receive only the conversation messages and a customer-safe view: whether an offer exists, product name, product summary, channel, country, and the safe outcome of an executed action. It SHALL NOT receive propensity, expected value, conversion value, send cost, candidate rankings, historical support, decision codes, customer model features (such as gender, marital status, age, income, or credit score), or the names of the model, engine, or workflow framework.

#### Scenario: Prompt payload contents
- **WHEN** any chat turn is processed for an ACTION customer
- **THEN** every payload sent to the LLM contains none of the forbidden fields or their values

#### Scenario: No offer in the view
- **WHEN** the engine decision is not `ACTION`
- **THEN** the view sent to the LLM states that no offer exists and contains no product, summary, or channel

### Requirement: Supported explanations only
Replies SHALL explain relevance only in general terms backed by the customer-safe view, such as "Based on the information available about your account, this appears to be a relevant option for you." Replies SHALL NOT claim facts the service does not hold, such as recent interactions, currently owned products, spending habits, or personal circumstances.

#### Scenario: Customer asks why
- **WHEN** an ACTION customer asks why the product fits them
- **THEN** the reply gives a general, account-based explanation and states no unsupported personal facts

### Requirement: Output guard
Before returning a reply, the service SHALL check it for forbidden internal terms, including model, engine, and framework names and the words propensity, expected value, ranking, and score. If any is found, it SHALL return a fixed safe reply instead, without changing `intent`, `action_taken`, or `execution_result`.

#### Scenario: Reply mentions an internal term
- **WHEN** the LLM produces a reply that contains "propensity"
- **THEN** the returned `reply` is the fixed safe reply and the action fields are unchanged

### Requirement: Reply language
A reply written by the LLM SHALL be in the language of the customer's latest message. Fixed fallback and safe replies, which are returned without the LLM, SHALL contain the same message in Spanish and English.

#### Scenario: Spanish message
- **WHEN** the latest message is written in Spanish
- **THEN** the reply is in Spanish

#### Scenario: Fixed reply
- **WHEN** the output guard replaces a reply
- **THEN** the returned reply contains the safe message in both Spanish and English

### Requirement: Stateless chat
Each `POST /agent/chat` SHALL be processed using only the request body and the loaded artifacts. The service SHALL NOT store conversation history, session state, or graph checkpoints between requests, and SHALL NOT require a session or thread identifier.

#### Scenario: Independent requests
- **WHEN** two requests carry the same customer and history
- **THEN** each is processed without reading anything stored by the other

### Requirement: Provider configuration
The LLM provider credentials and model identifier SHALL be read from environment variables at startup. Credentials SHALL NOT be included in the container image, written to logs, or returned in any response.

#### Scenario: Credentials stay out of responses
- **WHEN** any chat request succeeds or fails
- **THEN** no response body or log line contains the provider credential
