# Proposal

## Why

`POST /agent/chat` exists but can only be exercised through Swagger or `curl`, which hides the customer-facing experience it was built for. A Customer Agent tab in the existing demo page shows that experience next to the Decision Engine view, so a presenter can move between "what the bank decides" and "what the customer hears" for the same customer.

## What Changes

- Split the demo page into two tabs below the existing customer bar: **Decision Engine** (the current cards, unchanged and selected by default) and **Customer Agent** (new).
- The customer bar stays shared: a customer loaded there is used by both tabs.
- The Customer Agent tab shows a chat transcript with customer and assistant messages, a text input (2,000 characters max), and a Send button. Each send calls `POST /agent/chat` with the loaded `customer_id` and the latest 20 messages of the in-memory history.
- While a reply is pending, the tab shows a typing indicator and disables the input and Send button.
- Chat history lives only in page memory and resets whenever a different customer is loaded.
- 404, 422, 502, 503, and connection errors from the chat are shown in the existing error banner. 503 tells the presenter that the chat agent is not configured.
- A debug panel, visually separate from the conversation, shows the last turn's `intent`, `action_taken`, and `execution_result`.
- The UI shows the backend's `reply` verbatim and contains no decision logic: it never decides, gates, or rewords anything.
- The UI endpoint allowlist grows from four to five endpoints with `POST /agent/chat`, and its test stays an exact-match check.

Out of scope: changes to customer-facing wording (owned by the backend), persistence of chat history, streaming, linking chat actions to the Decision Engine panels, new backend endpoints, and frontend frameworks or build steps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `demo-ui`: the allowed endpoints grow to five with `POST /agent/chat`; visible errors include 502 and 503; new requirements cover the tab layout, the chat conversation, history handling, the loading state, and the debug panel.

## Impact

- Code: `app/static/index.html` (tab bar, Decision Engine wrapper, Customer Agent tab), `app/static/app.js` (tab switching, chat state and rendering, one new endpoint in the existing `endpoints` map), `app/static/styles.css` (tabs, chat bubbles, typing indicator, debug panel).
- Backend: none. `/agent/chat` already exists.
- Tests: `tests/ui/test_ui.py` allowlist updated to five endpoints; markup checks for both tabs.
- Docs: README Demo UI section and manual checklist gain the Customer Agent tab.
- Dependencies: none.
