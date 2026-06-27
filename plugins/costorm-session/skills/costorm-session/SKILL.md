---
name: costorm-session
description: >-
  Run an interactive, human-in-the-loop Co-STORM research session: a steerable,
  turn-based discourse where multiple LLM experts and an LLM moderator debate a topic
  over web-grounded sources while you observe and steer, growing a shared dynamic mind
  map turn by turn, then synthesize a cited report from it. The session persists to disk
  and can be resumed. Use when the user wants to co-research a topic conversationally —
  directing the discussion, challenging claims, narrowing scope, or watching experts
  surface and resolve disagreements — rather than getting a one-shot report. Trigger on
  "Co-STORM", "collaborative research session", "interactive research", "let's research X
  together", "expert panel / roundtable on X", "steer the research", "build a mind map of
  X", or "resume my research session". Prefer over the one-shot storm-research and
  deep-research whenever the user wants to be in the loop turn by turn or steer scope;
  route to those instead when they want an autonomous report with no interaction.
---

# costorm-session

Reimplements Co-STORM (Stanford OVAL,
[paper](https://arxiv.org/abs/2408.15232) / [repo](https://github.com/stanford-oval/storm)) as a
native, interactive skill. Co-STORM treats research as a **roundtable**: LLM experts answer and ask,
a moderator injects novel questions, and the human steers — all accreting a **dynamic mind map**
(the shared conceptual space) that is finally synthesized into a cited report.

**Prime directive:** you never autonomously run the whole thing. You run a *loop* — surface each turn
to the human, persist state between turns, and let them steer. You are also the **sole manager of
`session_state.json`**: Read it before each change, apply the delta, Write it back.

## When to use

- **costorm-session (this skill)** — the user wants to *steer* research turn by turn and watch a
  mind map grow. Interactive, resumable.
- **storm-research** — an autonomous, one-shot, multi-perspective long-form *article* with a
  citation audit. No interaction.
- **deep-research** — one narrow question → a sharp, fact-checked *answer*.

## How it runs

Instruction-driven; no scripts. Experts and the moderator are `Agent` subagents spawned per turn
(independent experts in parallel via several Agent calls in one message), or simulated inline in
`observe`/low-budget sessions. Web tools are deferred — load with
`ToolSearch("select:WebSearch,WebFetch")` before use. Each subagent prompt is self-contained and
ends with the exact JSON to return (templates in `references/discourse-policy.md`).

Read all three references before running turns:
- `references/state-and-mindmap.md` — the `session_state.json` schema, ID-minting, update rules
  (read before touching state).
- `references/discourse-policy.md` — turn-selection heuristics, stop conditions, role prompts.
- `references/session-artifacts.md` — how to render `mind_map.md`, `transcript.md`, `report.md`, etc.

## Procedure

**1 — Start or resume.** Compute the slug (lowercase topic, non-alphanumerics→`-`, collapse, trim,
~60 chars). If `./costorm_sessions/<slug>/session_state.json` exists, **offer to resume**: Read it,
render the mind map + open questions, summarize where things stand, and continue the loop at
`session.status`. Otherwise ask **≤2 questions**: (a) topic + framing/goal; (b) interactivity —
`observe` / `steer` (default) / `drive` — plus, if natural, expert count N (default 3, range 2–5),
any named perspectives, and a soft turn budget. Create `./costorm_sessions/<slug>/` and Write an
initial `session_state.json` (root concept `c_root` titled from the topic; empty rosters/lists;
`status:"warming"`; `turn_counter:0`).

**2 — Warm start.** Spawn **N expert subagents in parallel** (one per perspective). Each makes a
grounded opening contribution: 2–4 claims, each with a source anchor (url+title+snippet), plus one
follow-up question. Then **you** assemble the initial mind map — mint sources/concepts/claims/
questions (and any contradictions) per `state-and-mindmap.md`, cluster claims into 3–7 first-level
concepts under `c_root`, set `status:"active"` — and Write the file. Render the seeded mind map, then
pose a **moderator opening question** (novel, dissimilar to the experts' follow-ups). Hand control to
the loop per the interactivity mode.

**3 — Turn loop.** Each iteration:
- **Decide** the next move (`expert_answer` / `moderator_question` / `user_utterance` /
  `retrieval_expansion` / `consolidation`) using the heuristics in `discourse-policy.md`. In
  `steer`/`drive`, present the proposed move + 2–3 alternatives and wait for confirm/edit/override;
  in `observe`, pick autonomously but allow interrupts. A user interjection always preempts.
- **Execute** — spawn the role subagent(s) (parallel experts in one message) or simulate inline.
- **Integrate** the result into the mind map per `state-and-mindmap.md` (route/dedupe claims, attach
  source anchors, open/resolve contradictions, enqueue or answer questions, recompute coverage).
- **Persist** — Read→update→Write `session_state.json`; append a `turn_history` entry; bump
  `turn_counter`. Log any steering in `steering_log`.
- **Present** a compact changed-branches digest (and the move you propose next).
Continue until a stop condition (`discourse-policy.md`) holds.

**4 — Mind-map display.** After each turn, refresh `mind_map.md` and show the digest (full tree on
request), plus the open-question queue. This shared view is what the human steers against — keep it
visible.

**5 — Final report.** When stopping, first run a `consolidation` turn (clean up the tree), set
`status:"consolidating"`. Then synthesize `report.md` **from the mind map**: organize concepts into
an outline (overview → themes → debates/open tensions → open questions), draft each section grounded
**only** in that branch's claims/sources with `[n]` citations, present contradictions even-handedly,
and add an executive summary. For a polished long-form write-up you may spawn per-section subagents or
reuse the drafting/citation discipline from the `storm-research` skill's references. Write `report.md`,
`sources.md`, refreshed `mind_map.md`, `transcript.md` (from `turn_history`), and `open_questions.md`;
set `status:"reported"`. `SendUserFile` the report and note the session is resumable.

## Output artifacts (`./costorm_sessions/<slug>/`)

`session_state.json` (source of truth) + derived views `mind_map.md`, `transcript.md`, `report.md`,
`sources.md`, `open_questions.md`.

## Guardrails

- **Stay in the loop.** Don't silently auto-run many turns in `steer`/`drive`; the human steers.
- **State discipline.** Always Read `session_state.json` immediately before Writing it; mint ids by
  scanning current maxima; never write it partially. (No script guards this — you do.)
- **No fabrication.** Experts cite only pages they actually fetched; drop unfetchable sources. If
  web tools are unavailable, say so rather than inventing sources.
- **Preserve disagreement.** Open contradiction nodes instead of averaging conflicting claims;
  present them as contested in the report.
