# Session state & mind map

`session_state.json` is the single source of truth for a Co-STORM session. There is **no helper
script** — the main agent owns this file. The discipline below is what keeps it consistent across
turns and across resumes; follow it exactly.

## Read → update → write discipline

1. **Read** `session_state.json` immediately before every mutation (never edit from memory — the
   file may have changed across a long turn).
2. **Mint IDs** by scanning the current file for the max numeric suffix per prefix and incrementing
   (see below). Never reuse an id.
3. **Apply** the turn's delta in dependency order: sources → concepts → claims → questions →
   contradictions (so a thing exists before another references it).
4. **Write** the whole file back in one Write. Never leave it partially updated. Then bump
   `session.turn_counter`, set `session.updated_at` if you track time, and append a `turn_history`
   entry.

## ID conventions

Prefix per entity type, numeric suffix, monotonic, never reused:

| prefix | entity        | example |
|--------|---------------|---------|
| `c_`   | concept       | `c_1`   |
| `cl_`  | claim         | `cl_1`  |
| `s_`   | source        | `s_1`   |
| `q_`   | question      | `q_1`   |
| `x_`   | contradiction | `x_1`   |
| `exp_` | expert        | `exp_1` |

`c_root` is the reserved id of the root concept (the topic itself).

## Schema

```jsonc
{
  "schema_version": 1,
  "session": {
    "topic": "string",
    "slug": "string",
    "framing": "string",                 // goal/scope, may be ""
    "status": "warming | active | consolidating | reported",
    "turn_counter": 0                     // index of the NEXT turn
  },
  "preferences": {
    "interactivity": "observe | steer | drive",
    "max_turns": 20,                      // soft target
    "searches_per_turn": 3,
    "report_style": "report | brief"
  },
  "experts": [
    { "id": "exp_1", "name": "Health-policy economist",
      "perspective": "cost/access trade-offs", "expertise": ["health economics"],
      "active": true, "turns_taken": 0 }
  ],
  "mind_map": {
    "root_concept_id": "c_root",
    "concepts": [
      { "id": "c_root", "parent_id": null, "title": "string", "summary": "",
        "coverage": "uncovered|thin|covered", "claim_ids": [], "question_ids": [],
        "status": "open|consolidated", "created_turn": 0, "updated_turn": 0 }
    ]
  },
  "claims": [
    { "id": "cl_1", "concept_id": "c_2", "text": "the assertion",
      "stance": "assertion|caveat|counterpoint", "source_ids": ["s_1"],
      "raised_by": "exp_1|moderator|user", "confidence": "low|medium|high",
      "used": false, "created_turn": 1 }
  ],
  "sources": [
    { "id": "s_1", "url": "https://...", "title": "...", "publisher": "",
      "snippet": "evidence quote", "cited_by_claim_ids": ["cl_1"] }
  ],
  "unresolved_questions": [
    { "id": "q_1", "text": "...", "concept_id": "c_2|null",
      "raised_by": "exp_2|moderator|user", "novelty": 0.0,
      "status": "open|answered|dropped", "created_turn": 1, "answered_by_turn": null }
  ],
  "contradictions": [
    { "id": "x_1", "concept_id": "c_2", "claim_ids": ["cl_3","cl_4"],
      "description": "nature of the conflict", "status": "open|resolved",
      "resolution": null, "created_turn": 2 }
  ],
  "turn_history": [
    { "turn": 1, "type": "warm_start|expert_answer|moderator_question|user_utterance|"
                          "retrieval_expansion|consolidation",
      "actor": "exp_1|moderator|user|system", "input_question_id": "q_1|null",
      "content": "verbatim utterance/answer (for the transcript)",
      "delta": { "concepts_added": [], "claims_added": [], "sources_added": [],
                 "questions_raised": [], "questions_resolved": [],
                 "contradictions_opened": [], "contradictions_resolved": [],
                 "consolidation_ops": [] } }
  ],
  "steering_log": [
    { "turn": 4, "kind": "narrow_scope|challenge_claim|request_example|restrict_sources|"
                          "reprioritize|add_claim",
      "text": "what the user asked for", "target_id": "cl_3|c_2|null" }
  ]
}
```

Hierarchy lives only in `concepts[].parent_id`; everything else references by id. Keep the lists flat
— it makes merges, dedupe, and contradiction-linking cheap.

## Update rules

**Routing a new claim.** Attach it to the existing concept it best fits (add its id to that
concept's `claim_ids`, set the claim's `concept_id`). If it fits no existing concept, create a child
concept under the most relevant parent and attach there. Set `raised_by` and `confidence`. New
grounded claims must have ≥1 `source_id`.

**Dedupe.** Before adding a claim, check for a near-identical existing claim on the same concept; if
found, merge source anchors into the existing claim instead of adding a duplicate. Dedupe sources by
normalized URL (lowercase host, strip `www.`, drop `utm_*`/`fbclid`/fragments/trailing slash) — one
`s_` id per page; reuse it across claims.

**Contradiction vs caveat.** If a new claim directly conflicts with an existing claim's assertion
(they can't both be true as stated), open a `contradiction` linking both claim ids and set both
claims' `stance` appropriately. If the new claim only qualifies or limits an existing one, add it as
a claim with `stance: "caveat"` or `"counterpoint"` — no contradiction node.

**Questions.** A new follow-up becomes an `unresolved_question` (`status: "open"`). When a later turn
answers it, set `status: "answered"` and `answered_by_turn`. If it becomes irrelevant (scope changed,
superseded), set `status: "dropped"`. The moderator favors high-`novelty` open questions.

**Coverage recomputation** (run for every touched concept):
- `uncovered` — 0 claims.
- `thin` — 1–2 claims, or claims drawn from a single source.
- `covered` — ≥3 claims from ≥2 distinct sources.
Coverage drives turn policy (see `discourse-policy.md`): thin/uncovered concepts on a live question's
path pull expert turns; well-covered branches free the moderator to push novelty elsewhere.

## Consolidation ops

A `consolidation` turn reorganizes the map without adding content. Record each op in the turn's
`delta.consolidation_ops` and apply it:

- `merge_concepts {from, into}` — re-point all child concepts, claims, and questions from `from` to
  `into`, fold any contradictions, then delete `from`.
- `reparent {concept, new_parent}` — change `parent_id`.
- `retitle {concept, title}` / `set_summary {concept, summary}` — relabel/refresh.
- `set_coverage {concept, coverage}` — override coverage after restructuring.

Run a consolidation pass when the tree grows noisy (many near-duplicate concepts, orphan claims) and
always once right before generating the final report.

## Worked example (two turns)

Start: `c_root = "Carbon capture for cement"`, status `warming`.

**Turn 1 — expert_answer (exp_1):** returns two grounded claims. The agent mints `s_1`, `s_2`,
creates `c_1 "Capture technologies"` (child of `c_root`), adds `cl_1` (→`c_1`, source `s_1`,
confidence high) and `cl_2` (→`c_1`, source `s_2`). `c_1.coverage` → `thin` (2 claims, 2 sources →
still thin by the 1–2-claim rule). Raises `q_1 "What is the energy penalty?"` (novelty 0.6).
`turn_history[+1]`, `turn_counter → 2`.

**Turn 2 — expert_answer (exp_2)** answering `q_1`: returns a claim that the energy penalty is
"modest" — but `cl_1` implied it is large. The agent mints `s_3`, adds `cl_3` (→`c_1`), detects the
conflict with `cl_1`, and opens `x_1 {concept: c_1, claim_ids:[cl_1, cl_3], description:"energy
penalty magnitude disputed", status:"open"}`. Marks `q_1` `answered` (`answered_by_turn: 2`).
`c_1.coverage` → `covered` (3 claims, 3 sources). Write, append history, `turn_counter → 3`.
