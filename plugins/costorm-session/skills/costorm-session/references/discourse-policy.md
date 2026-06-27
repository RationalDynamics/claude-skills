# Discourse policy

How the loop decides the next move, when it stops, and how the role subagents behave. Read this
before running any non-warm-start turn.

## Turn types

| Type                 | What happens | Pick when |
|----------------------|--------------|-----------|
| `expert_answer`      | An expert subagent answers the question on the table, grounded in web sources. | There is a high-novelty open question, or a `thin`/`uncovered` concept on a live question's path. |
| `moderator_question` | The moderator injects one novel, thought-provoking question. | Open-question novelty is low, the discussion is circling one branch, or unused/uncited info is piling up. |
| `user_utterance`     | The human steers. | Whenever the user interjects — this **always preempts** the planned move. |
| `retrieval_expansion`| A lightweight retrieval subagent adds sources to an existing claim/concept (no full expert turn). | A claim is `low` confidence or contested, or a concept is `thin`/uncited. |
| `consolidation`      | Reorganize the mind map (merge/reparent/retitle/summarize); no new content. | The tree is noisy (near-duplicate concepts, orphan claims), or right before the report. |

## Turn-selection heuristics

Each turn, score the signals and pick the highest-value move:

1. **User first.** If the user has just spoken, route their intent (a `user_utterance` turn) and let
   it shape the *next* expert/moderator turn.
2. **Coverage gap.** Prefer an `expert_answer` aimed at the most-relevant `uncovered`/`thin` concept
   that sits on the path of an open question.
3. **Open-question novelty.** If the best open question has high novelty, answer it (expert). If all
   open questions are low-novelty/answered, switch to `moderator_question` to break the rut.
4. **Unused info.** If retrieval has surfaced sources/snippets not yet folded into claims, that's a
   cue for the moderator to ask about them, or for a `retrieval_expansion` to attach them.
5. **Contradictions.** An open contradiction is high-value — direct an expert (or the user's
   attention) at resolving it.
6. **Hygiene.** When concept count balloons or duplicates accumulate, spend a `consolidation` turn.

**Question novelty** = dissimilarity of a candidate question to all prior question texts (lexical/
semantic overlap — lower overlap = higher novelty). The moderator maximizes novelty *and* relevance
to the topic; it should not re-ask near-duplicates of earlier questions.

## Interactivity modes

- **observe** — pick moves autonomously and run them; surface a digest each turn; the user may
  interrupt at any time. Inline role simulation is fine here to keep it moving.
- **steer** (default) — propose the next move (plus 2–3 alternatives) and pause for the user to
  confirm / edit / override before executing.
- **drive** — the user approves or edits every move; never run a turn without their go-ahead.

Fold an override back in: if the user redirects, log it in `steering_log`, adjust the planned move,
and (when relevant) enqueue or re-prioritize the affected questions/concepts.

## Stop conditions

End the loop (and offer the report) when any holds: the soft `max_turns` budget is reached; the user
says stop / "write the report"; all `unresolved_questions` are `answered`/`dropped`; or the
moderator's best new question falls below a novelty floor (~0.3) while coverage is broad.

## Spawn vs simulate

Spawn an `Agent` subagent for a role when you want genuine independence and parallel web research —
e.g. several experts in one turn (issue the Agent calls in a single message to run them
concurrently). Simulate a role inline (you play it, using WebSearch/WebFetch yourself) in `observe`
mode or low-budget sessions where the overhead of a subagent isn't worth it. Either way the output
must match the JSON shapes below so it folds cleanly into `session_state.json`.

## Role prompt templates

Fill the `<...>` and give the agent the **current mind-map digest** (a compact text rendering of the
relevant branch + the open questions) so it has context without the whole JSON. Each template ends
with the exact JSON to return. (Source objects use placeholder ids the main agent re-mints to `s_`.)

### Expert

> You are **<expert.name>**, an expert on **<topic>** with the perspective: <expert.perspective>.
> The question on the table is: **<question text>**. Current map digest: <digest>.
>
> Load web tools (`ToolSearch select:WebSearch,WebFetch`), then answer in your own voice, grounded
> in sources you actually fetch (up to <searches_per_turn> searches). Give 2–4 atomic claims, each
> with a source anchor (url + title + snippet). If you disagree with an existing claim, say so
> explicitly. Raise up to 2 follow-up questions from your perspective. Do not invent sources.
>
> Return ONLY:
> ```json
> { "content": "your spoken answer (prose, for the transcript)",
>   "claims": [{"text":"...","stance":"assertion|caveat|counterpoint",
>               "source":{"url":"...","title":"...","publisher":"","snippet":"..."},
>               "confidence":"low|medium|high",
>               "conflicts_with":"<existing claim text or ''>"}],
>   "follow_up_questions": ["..."] }
> ```

### Moderator

> You are the moderator of a research roundtable on **<topic>**. Map digest: <digest>. Prior
> questions asked: <list of question texts>.
>
> Inspect the under-explored concepts and any retrieved-but-unused information. Emit exactly ONE
> novel, thought-provoking question that (a) is highly relevant to the topic and (b) is maximally
> dissimilar from the prior questions — open a new angle, don't rephrase an old one.
>
> Return ONLY: `{ "question": "...", "targets_concept": "<concept title or ''>",
> "novelty": 0.0-1.0, "rationale": "why this opens new ground" }`

### Retrieval (expansion)

> Find corroborating or opposing sources for this claim/concept on **<topic>**: <claim or concept>.
> Load web tools, run up to <searches_per_turn> searches, fetch the best pages.
>
> Return ONLY: `{ "sources": [{"url":"...","title":"...","publisher":"","snippet":"...",
> "supports": true}], "note": "what this changes (e.g. confirms / contradicts / adds nuance)" }`
