# Design

## Context

See `proposal.md` for motivation and `specs/demo-ui/spec.md` for behavior. Current state:

- `app/static/index.html` has one `<main class="layout">` holding the customer bar, the error banner, and four cards (recommendation, candidates, execute, LangGraph workflow).
- `app/static/app.js` keeps page state in one object (`state = {customerId, decision, country}`), builds every API path in one `endpoints` map, calls the API only through `api()`, which returns typed results (`ok`, `http`, `network`), and reports failures through one `showError()` banner. `syncControls()` derives every button's enabled state from `state`, and `withBusy()` wraps a request with a button's loading state.
- `loadCustomer()` sets `state` only after a successful load, then calls `resetPanels()`.
- `tests/ui/test_ui.py` extracts every path literal in `app.js` and requires it to equal the allowed set exactly.
- `POST /agent/chat` is stateless: the client sends `customer_id` and up to 20 messages ending with a `user` message; content is 1 to 2,000 characters.

## Goals / Non-Goals

**Goals:** Add the Customer Agent tab by extending the existing patterns (one state object, one client, one banner, one endpoint map) without touching the Decision Engine cards' internals.

**Non-Goals:** Routing or URL state for tabs, a component library, chat persistence, markdown rendering of replies, accessibility beyond semantic tab roles and labels, and syncing chat actions into the Decision Engine panels.

## Decisions

1. **Tabs as two sibling panels toggled with the `hidden` attribute.** A `role="tablist"` with two `role="tab"` buttons sits below the error banner. The existing four cards move unchanged into `<div id="tab-decision" role="tabpanel">`; the chat goes in `<div id="tab-agent" role="tabpanel" hidden>`. Switching only flips `hidden` and `aria-selected`, so no data reloads and both tabs keep their content. *Alternative:* re-rendering a tab on switch. Rejected: it would reload or rebuild state for no benefit.

   ```
   main.layout
   +-- customer bar            (unchanged, shared)
   +-- error banner            (unchanged, shared)
   +-- tablist                 (new)
   +-- #tab-decision           (existing 4 cards, moved as-is)
   +-- #tab-agent  [hidden]    (new: transcript + form | debug panel)
   ```

2. **Chat state extends the existing state object.** `state.chat = {messages: [], pending: false}`. `loadCustomer()` resets `state.chat` only when the loaded ID differs from the previous `state.customerId`, then calls a `renderChat()`. `syncControls()` also sets the chat input and Send button: enabled only when a customer is loaded and no chat request is pending. One place still decides every control's state.

3. **Send flow.**

   ```
   submit --> trim; empty? stop
          --> push {role: user} ; render ; pending=true ; show typing
          --> api("POST", endpoints.chat(), {customer_id, messages: last 20})
          --> ok:   push {role: assistant, content: reply} ; render debug
              fail: pop the user message ; restore input text ; showError()
          --> pending=false ; hide typing ; syncControls()
   ```

   The 20-message window is `messages.slice(-20)` taken after the new user message is appended, so it always ends with that message. Failed messages are removed so the history never holds a customer message the backend did not answer.

4. **One new endpoint in the existing map.** `endpoints.chat = () => "/agent/chat"`. The allowlist test gains this path and stays an exact-match check, so any further endpoint still needs a spec change.

5. **Errors reuse `showError()`.** Its title map gains `502: "Chat agent error"` and `503: "Unavailable"`; the API `detail` already carries the reason (for 503, that no LLM provider is configured). The banner sits above the tabs, so it is visible from either tab.

6. **Rendering is text-only.** Messages are created with `textContent`, never `innerHTML`, so a reply or a customer message cannot inject markup. Customer bubbles align right, assistant bubbles left. The typing indicator is a muted assistant-side bubble that is shown and hidden, not a message in the history.

7. **Debug panel beside the transcript.** A separate card titled "Debug (last turn)" renders `intent`, `action_taken`, and `execution_result` with the existing `renderFields()` helper and a muted style. It is cleared with the chat. Nothing from it enters the transcript.

8. **No frontend decision logic.** The tab never reads `state.decision`; NO CONSENT customers chat like any other, and the backend decides what to say and do.

## Risks / Trade-offs

- [No automated tests for chat behavior] → Logic stays small and goes through the existing client and banner; the README manual checklist covers every scenario, consistent with how the demo UI is verified today.
- [A chat confirm or handoff does not update the Decision Engine panels] → Intentional; the debug panel shows the execution result for the chat turn.
- [Two LLM calls make replies take a few seconds] → The typing indicator and disabled input make the wait explicit.
- [The header tagline names the model and the workflow framework on both tabs] → Accepted for a demo audience; it is page chrome, not customer conversation.

## Migration Plan

Static files only. Rebuild the image or reload the page. Rollback means reverting the change's commits.
