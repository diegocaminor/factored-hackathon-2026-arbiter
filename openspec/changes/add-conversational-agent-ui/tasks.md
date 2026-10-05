# Tasks

## 1. Tab layout

- [ ] 1.1 In `index.html`, add the tablist below the error banner, move the four existing cards unchanged into `#tab-decision`, and add an empty `#tab-agent` panel (hidden); in `app.js`, add tab switching that only toggles `hidden` and `aria-selected`; in `styles.css`, style the tabs. Verify with `tests/ui/test_ui.py` assertions that both tabs and panels exist with Decision Engine selected by default, the existing card IDs are still present, the suite passes, and in a browser the Decision Engine tab works as before and keeps its content across tab switches.

## 2. Customer Agent chat

- [ ] 2.1 Build the Customer Agent panel markup and styles: transcript, typing indicator, form with a `maxlength="2000"` input and Send button, the load-a-customer hint, and a separate "Debug (last turn)" card. Verify with test assertions that these elements exist, the input has `maxlength="2000"`, and the files contain no external URLs.
- [ ] 2.2 Implement the chat in `app.js` per design decisions 2 to 8: `endpoints.chat`, `state.chat`, reset on customer change, controls in `syncControls()`, send flow with the 20-message window, failed-send rollback, `textContent` rendering, debug panel, and the 502 and 503 titles in `showError()`. Update `ALLOWED_API_PATHS` in `tests/ui/test_ui.py` to the five endpoints and verify the exact-match test passes.

## 3. Docs and verification

- [ ] 3.1 Update the README Demo UI section with the two tabs, what the Customer Agent tab and its debug panel do, the `OPENAI_API_KEY` requirement for chat, and new manual checklist steps. Verify by running them end to end in a browser against the Docker image with mounted artifacts and a key: chat disabled before loading; recommendation, why, and confirm turns for `CLI-P21780PQ8D9W` with the debug panel showing `OFFER_CONFIRMED`; a Spanish message answered in Spanish; a NO CONSENT customer chatting without an offer; the chat resetting when another customer loads; the Decision Engine tab unchanged across switches; and the 503 banner with a container started without the key. Run the full test suite and `openspec validate add-conversational-agent-ui --strict`.
