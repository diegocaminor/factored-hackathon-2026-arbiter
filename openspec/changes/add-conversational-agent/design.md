# Design

## Context

See `proposal.md` for motivation and `specs/conversational-agent/spec.md` for behavior. Current state:

- `NBAService.recommend(customer_id)` returns the engine decision, product, channel, and economic values; `NBAService.has_customer()` checks existence.
- `ExecutionService.confirm()` recomputes the recommendation itself and raises `RecommendationNotActionable` unless the decision is `ACTION`. `ExecutionService.handoff()` accepts a reason. Both sit behind ports (`OfferSender`, `HandoffQueue`) with simulated adapters.
- Product summaries live in `PRODUCT_DETAILS` / `get_product_details_tool()` in the vendored `propensity.langgraph_nba_agent`, which `/agent/run` already uses.
- `app/main.py` builds every service once in the lifespan and stores it on `app.state`.
- No LLM dependency exists today. Customer snapshot features include sensitive attributes (gender, marital status, age, income, credit score) and no interaction history or product holdings.

## Goals / Non-Goals

**Goals:** A chat turn whose consequential behavior is fully decided by code, testable end to end with a fake model, and impossible to leak internals through by construction rather than by prompt wording.

**Non-Goals:** Tool-use loops, multi-step agent planning, streaming, prompt tuning beyond a working baseline, an eval harness, reusing or changing the LangGraph graph.

## Decisions

1. **Two LLM calls per turn: classify, then write.** Code runs between them.

   ```
   request --> validate --> customer exists? --404--> stop
                                  |
                          recommend (NBA engine)
                                  |
                          build SafeView
                                  |
           ChatModel.classify(messages, view) --error--> 502
                                  |
           dispatch(intent, decision) --> confirm / handoff / nothing
                                  |
           ChatModel.write_reply(messages, view, intent, outcome)
                 |                                 |
               reply                         error -> fixed fallback
                 |
           output guard --forbidden term--> fixed safe reply
                 |
              response
   ```

   *Alternative:* a tool-use loop where the LLM calls `confirm_offer` itself. Rejected: it gives the model execution authority and makes gates depend on prompt compliance. A single call returning intent and reply together was also rejected, because the reply must describe an outcome that only exists after dispatch.

2. **`ChatModel` port with two methods.** `classify(messages, view) -> Intent` and `write_reply(messages, view, intent, outcome) -> str`. The production adapter uses the Anthropic SDK; tests use a scripted fake that records every payload it receives. This mirrors the existing `OfferSender` / `HandoffQueue` port pattern, and keeps the service free of SDK types.

3. **Classification uses structured output constrained to the intent enum.** The adapter requests JSON matching `{"intent": <one of 7 values>}` and validates it with Pydantic. A refusal stop reason, invalid JSON, or an unknown value counts as an unusable result (HTTP 502 for classification). The latest user message is the classification target; earlier messages are context only.

4. **`SafeView` is the only data path to the LLM.** A frozen Pydantic model built from the engine response and product details, holding exactly `has_offer`, `product`, `product_summary`, `channel`, `country`, and `outcome`. When the decision is not `ACTION`, product fields are `None` and `has_offer` is `False`. The decision code is never copied, so the model cannot reveal it. The adapter serializes only `SafeView` and the message list, so a forbidden field can only reach the model by adding it to `SafeView`, which the tests guard.

5. **Dispatch table in code.**

   | Intent | Decision | Action | `action_taken` |
   |---|---|---|---|
   | `REQUEST_RECOMMENDATION`, `ASK_WHY`, `ASK_PRODUCT` | any | none | `NONE` |
   | `CONFIRM` | `ACTION` | `ExecutionService.confirm()` | `OFFER_CONFIRMED` |
   | `CONFIRM` | not `ACTION` | none; reply asks for clarification | `NONE` |
   | `DECLINE` | any | none | `NONE` |
   | `REQUEST_HUMAN` | any | `ExecutionService.handoff(fixed reason)` | `HANDOFF_CREATED` |
   | `UNCLEAR` | any | none; reply asks for clarification | `NONE` |

   Reusing `ExecutionService` gives parity with `/confirm` and `/handoff` for free, and `confirm()` re-checks `ACTION` as a second gate. The handoff reason is a constant, so the LLM never writes into an execution payload.

6. **`outcome` is a safe summary, not the execution payload.** For example `{"type": "offer_sent", "channel": "Push"}` or `{"type": "advisor_requested"}`. `provider_message_id` and queue names stay out of the prompt; the full `execution_result` goes only into the HTTP response.

7. **Output guard is a case-insensitive deny-list** over the reply: `catboost`, `propensity`, `expected value`, `next best action`, `nba`, `langgraph`, `ranking`, `score`, `model`, and `algorithm`, matched on word boundaries. A match returns the fixed bilingual safe reply. It is defense in depth behind decision 4, not the primary control, so false positives (a customer-facing "model" in another sense) are acceptable.

8. **Fixed replies are bilingual constants** (Spanish then English), because they are produced without the LLM and cannot detect the language. There are three: safe reply (guard), fallback after an action ran (one per outcome type), and nothing else. Classification failure is an HTTP 502, not a reply.

9. **Configuration and 503.** `ANTHROPIC_API_KEY` enables the provider; `CHAT_MODEL` selects the model and defaults to `claude-opus-5-5`. At startup, `app.state.chat_service` is built only when the key is a non-empty string; otherwise it is `None` and the router dependency raises 503. The SDK client is created once. *Alternative:* failing startup without a key. Rejected: the NBA, execution, and agent endpoints and the demo UI must keep working offline.

10. **Model call settings.** Both calls use low effort (classification and short customer replies do not benefit from deeper reasoning), a bounded `max_tokens`, a short timeout, and the SDK's default retries. The system prompts are static strings, so they are cache-friendly, and they state the persona, the reply-language rule, the supported-explanations rule with the approved example phrasing, and the "never present an offer when `has_offer` is false" rule. Refusals are handled as unusable results per decision 3; server-side refusal fallbacks are enabled on the request.

11. **Package layout.** New `app/chat/` with `router.py`, `schemas.py` (request, response, `Intent`, `ActionTaken`), `service.py` (orchestration and dispatch), `safe_view.py`, `guard.py`, and `model.py` (port plus Anthropic adapter). The router depends only on `ChatService`.

## Risks / Trade-offs

- [The LLM misclassifies a message as `CONFIRM`] → Only the latest message counts, the decision must be `ACTION`, and the action is a simulated send. The classification prompt tells the model to choose `UNCLEAR` when consent is not explicit.
- [The LLM states unsupported facts despite the prompt] → It only sees the safe view, so there are no personal facts to misuse; the system prompt forbids the rest. Not machine-verifiable beyond the guard; covered by the manual checklist.
- [The deny-list misses a paraphrase of an internal concept] → The data was never sent, so a paraphrase cannot carry real values.
- [Two LLM calls add latency] → Low effort and short outputs. Acceptable for a demo turn.
- [Client-supplied history can be forged] → History is never trusted for product, channel, or consent beyond the latest message, and the engine is recomputed each turn.
- [Fixed bilingual replies read awkwardly] → They occur only on guard hits or provider failures after an action.
- [New runtime dependency and secret] → The key is read from the environment at run time, never baked into the image, never logged.

## Migration Plan

Additive. Install the new dependency and rebuild the image. Run with `-e ANTHROPIC_API_KEY=...` (and optionally `-e CHAT_MODEL=...`) to enable chat; without them, everything else behaves as today. Rollback means reverting the change's commits.
