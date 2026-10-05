# Spec Delta

## MODIFIED Requirements

### Requirement: API-only data access
The UI SHALL obtain all data by calling only `GET /customers/{customer_id}/next-best-action`, `POST /customers/{customer_id}/confirm`, `POST /customers/{customer_id}/handoff`, `POST /agent/run`, and `POST /agent/chat`. Serving the UI SHALL NOT add any backend endpoint for customer discovery, graph tracing, or observability. The UI SHALL NOT import ML modules or read artifacts.

#### Scenario: Only existing endpoints are referenced
- **WHEN** the UI's JavaScript is inspected
- **THEN** every API path it calls is one of the five endpoints listed above, and all five are used

### Requirement: Visible errors
The page SHALL show a visible message, rather than failing silently, when the API returns 404, 409, 422, 502, or 503, or when the request cannot reach the server. The message SHALL include the API's `detail` text when one is returned.

#### Scenario: Unknown customer
- **WHEN** the user loads a customer ID that does not exist
- **THEN** the page shows a not-found message containing the API's `detail`

#### Scenario: Server unreachable
- **WHEN** the API cannot be reached
- **THEN** the page shows a connection error message

#### Scenario: Chat agent not configured
- **WHEN** the user sends a chat message and the API responds with 503
- **THEN** the page shows a message stating the chat agent is unavailable, including the API's `detail`

## ADDED Requirements

### Requirement: Tabbed layout
Below the customer bar, the page SHALL offer two tabs: `Decision Engine`, selected by default, and `Customer Agent`. The Decision Engine tab SHALL contain the existing recommendation, candidates, execution, and agent workflow panels with their behavior unchanged. Switching tabs SHALL NOT reload data or clear either tab's content.

#### Scenario: Default tab
- **WHEN** the page opens
- **THEN** the Decision Engine tab is selected and shows the existing panels

#### Scenario: Switching tabs keeps content
- **WHEN** a customer is loaded, the user switches to Customer Agent and back
- **THEN** the Decision Engine panels still show that customer's recommendation without a new request

### Requirement: Shared customer selection
The customer bar SHALL stay above both tabs, and the customer loaded there SHALL be the customer used by the Customer Agent tab. Until a customer is loaded, the chat input and Send button SHALL be disabled with a visible hint.

#### Scenario: Chat before loading a customer
- **WHEN** no customer is loaded and the user opens Customer Agent
- **THEN** the input and Send button are disabled and the tab asks the user to load a customer

#### Scenario: Chat uses the loaded customer
- **WHEN** the user loads `CLI-P21780PQ8D9W` and sends a chat message
- **THEN** the request to `POST /agent/chat` carries `customer_id` `CLI-P21780PQ8D9W`

### Requirement: Chat conversation
The Customer Agent tab SHALL show a transcript of customer and assistant messages in order, visually distinguished, with a text input limited to 2,000 characters and a Send button. Sending SHALL call `POST /agent/chat` and append the backend's `reply` to the transcript verbatim. Empty or whitespace-only messages SHALL NOT be sent.

#### Scenario: Successful turn
- **WHEN** a customer is loaded and the user sends "What do you recommend for me?"
- **THEN** the transcript shows the customer message followed by the assistant's `reply` exactly as returned

#### Scenario: Empty message
- **WHEN** the input is empty or contains only spaces and the user presses Send
- **THEN** no request is made

### Requirement: In-memory chat history
The chat history SHALL live only in page memory. Each request SHALL send the latest 20 messages of the history, ending with the new customer message. The history and transcript SHALL reset when a different customer is loaded. If a send fails, the unsent customer message SHALL be removed from the history and transcript and restored to the input.

#### Scenario: Long conversation
- **WHEN** the history already holds 20 messages and the user sends another
- **THEN** the request carries exactly the latest 20 messages, the last being the new customer message

#### Scenario: Customer changes
- **WHEN** a conversation exists and the user loads a different customer
- **THEN** the transcript and history are empty

#### Scenario: Failed send
- **WHEN** the API responds with an error to a chat message
- **THEN** the error banner is shown, the message is no longer in the transcript, and its text is back in the input

### Requirement: Chat loading state
While a chat request is pending, the tab SHALL show a typing indicator and SHALL disable the input and Send button. Both SHALL be re-enabled when the request completes or fails.

#### Scenario: Waiting for a reply
- **WHEN** a chat request is in flight
- **THEN** a typing indicator is visible and the input and Send button are disabled

### Requirement: Debug panel
The Customer Agent tab SHALL include a debug panel, visually separate from the transcript, showing the last turn's `intent`, `action_taken`, and `execution_result`. Debug values SHALL NOT appear inside the customer conversation.

#### Scenario: Turn with an action
- **WHEN** a turn returns `action_taken` `OFFER_CONFIRMED`
- **THEN** the debug panel shows the intent, `OFFER_CONFIRMED`, and the execution result, and the transcript shows only the reply

### Requirement: Backend-owned conversation
The UI SHALL NOT decide, gate, or alter chat behavior: it SHALL send every non-empty message regardless of the customer's decision, SHALL NOT interpret intents to trigger actions, and SHALL NOT rewrite or supplement the backend's reply.

#### Scenario: NO CONSENT customer can chat
- **WHEN** a customer whose decision is `NO_ACTION_CONSENT` is loaded
- **THEN** the chat input is enabled and messages are sent to the backend like for any other customer
