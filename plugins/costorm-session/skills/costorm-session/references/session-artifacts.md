# Session artifacts & rendering

All files live under `./costorm_sessions/<slug>/`. `session_state.json` is the durable source of
truth; every `.md` is a **derived view** regenerated from it, so a crash loses at most the in-flight
turn.

| File                 | What it is | Refreshed |
|----------------------|------------|-----------|
| `session_state.json` | Source of truth (schema in `state-and-mindmap.md`) | every turn |
| `mind_map.md`        | The concept tree, rendered | every turn + at report |
| `transcript.md`      | The discourse replayed as dialogue | every turn + at report |
| `report.md`          | Final synthesized report | at report generation |
| `sources.md`         | Numbered source table | at report generation |
| `open_questions.md`  | Open-question queue | every turn (interim) + final |

## `mind_map.md` — rendering contract

Indented tree from `mind_map.concepts` (follow `parent_id`), depth-first, root first. Markers:
`●` root · `├─`/`└─` branch concepts · `•` claim · `?` open question · `⚠` contradiction. Tag each
concept with its `[coverage]` and counts; tag each claim with its source ids `[s1,s3]`; end with a
source legend.

```
● Carbon capture for cement                     [covered]
  ├─ Capture technologies                        [covered] (3 claims, 1 open Q)
  │    • Amine scrubbing dominates pilots [s1]
  │    • Calcium looping is cheaper at scale [s2]   ⚠ disputes cl_1 (x_1, open)
  │    ? What is the energy penalty?  (answered)
  └─ Policy & cost                               [thin] (1 claim)
       • EU ETS makes capture viable above €90/t [s4]

Sources: s1 IEA 2023 · s2 Nature 2022 · s4 EU ETS data
```

Each turn, show a **digest** (only branches whose `updated_turn == turn_counter-1`, plus changed
questions/contradictions). Offer the full tree on request.

## `transcript.md` — rendering contract

Replay `turn_history` in order, one block per turn, using `content`:

```
[Turn 1 · expert] Health-policy economist:
<content>

[Turn 2 · moderator]:
<question>

[Turn 3 · you]:
<your utterance>
```

## `report.md` — rendering contract

Synthesized from the mind map (see SKILL.md step 5). Sections grounded only in the map's claims and
sources, with bracketed numeric citations `[1]`, `[2]` keyed to `sources.md`. Structure: title →
executive summary → thematic sections (overview → themes → debates/open tensions) → Open Questions →
References. Present contradictions even-handedly. Add no claim that isn't backed by a mind-map source.

## `sources.md` — rendering contract

Numbered table mapping the report's `[n]` markers to sources:

```markdown
| n | id | title | url | publisher |
|---|----|-------|-----|-----------|
| 1 | s_1 | IEA Cement Roadmap | https://... | IEA |
```

## `open_questions.md`

The `unresolved_questions` with `status: open`, sorted by `novelty` desc then recency, each with its
raiser and scoped concept.

## Resume contract

A session is resumable iff `./costorm_sessions/<slug>/session_state.json` exists and parses. To
resume: Read it, render `mind_map.md` and the open-question queue, summarize where things stand
(turn count, coverage, open contradictions), and continue the loop at `session.status`. The `.md`
views can always be rebuilt from the JSON, so never treat them as authoritative.
