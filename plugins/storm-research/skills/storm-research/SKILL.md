---
name: storm-research
description: >-
  Perspective-driven, outline-first long-form research that reimplements Stanford's
  STORM method: discover several expert perspectives on a topic, run a simulated
  research conversation per perspective (ask -> search -> follow-up) to gather cited
  claim-level evidence, build an evidence-grounded outline, then draft a Wikipedia-style
  article section by section with inline citations and a deterministic citation audit.
  Use when the user asks for a STORM report, a long-form / comprehensive / encyclopedic
  / Wikipedia-style write-up, a literature-style overview, or balanced multi-perspective
  coverage of a topic. Trigger on "write a long article on...", "multi-perspective
  overview of...", "STORM this topic", "research X like a Wikipedia page", or "deep
  cited report on...". Prefer over deep-research when the deliverable is a structured
  long-form ARTICLE with breadth of viewpoints rather than a focused answer to one narrow
  question; prefer costorm-session when the user wants to steer the research interactively.
---

# storm-research

Reimplements STORM (Stanford OVAL) as a native, instruction-driven research skill. STORM
produces cited, encyclopedic long-form by **researching before writing**: it asks questions
from multiple perspectives, simulates research conversations grounded in web search, builds an
evidence-grounded outline, drafts section by section with citations, then polishes.

You (the main agent) are the **orchestrator and synthesizer**. You fan out `Agent` subagents
for the parallel stages (per-perspective research, per-section drafting) and keep the heavy
retrieval out of your own context — only distilled, structured notes come back. You own the
outline, the synthesis, every file write, and the final citation audit.

## When to use

- **storm-research (this skill)** — broad topic → balanced, multi-perspective, sectioned
  long-form *article* with a citation audit. Autonomous, one-shot.
- **deep-research** — one narrow question → a sharp, adversarially fact-checked *answer*.
- **costorm-session** — the user wants to *steer* the research interactively (experts +
  moderator + their own turns) and watch a mind map grow, rather than receive a finished report.

## How it runs

Instruction-driven, no bundled orchestration scripts. Parallelize a stage by issuing **several
`Agent` calls in a single message** (they run concurrently). Use `general-purpose` subagents for
web research and section drafting; an `Explore` subagent is fine for the opening "survey related
articles" step. Web tools are deferred — before using them directly, load with
`ToolSearch("select:WebSearch,WebFetch")`. Every subagent prompt must be self-contained (it can
not read this skill's files): state its task, tell it to use WebSearch/WebFetch, forbid citing any
URL it did not actually fetch, and specify the exact return shape.

Read `references/storm-method.md` for the faithful method + the exact subagent prompt templates,
`references/source-policy.md` for sourcing rules, and `references/output-contracts.md` for the
JSON schemas and artifact file formats. The full schemas live there; field names below are a map.

## Procedure

**1 — Intake & brief.** Ask **2–4 clarifying questions only when underspecified** (bare-noun topic,
unknown audience/depth, ambiguous scope or timeframe); otherwise proceed. Build a research brief:
`{topic, angle, audience, depth, timeframe, must_cover[], exclude[], target_sections, target_words}`.
Compute the slug and create `./storm_runs/<slug>/` (lowercase topic, non-alphanumerics→`-`, collapse
repeats, trim, ~60 chars; suffix `-2/-3` on collision). Write `research_brief.md`.

**2 — Perspective discovery.** Optionally spawn one subagent to survey existing overview/encyclopedia
articles on the topic and return recurring themes + the kinds of experts/stakeholders who shape
coverage. Then derive **3–6 distinct, non-overlapping perspectives** (you may synthesize these
yourself). Each: `{id, name, focus, rationale, key_questions[3–5]}`. Write `perspectives.md`.

**3 — Research fan-out (parallel).** Spawn **one `general-purpose` subagent per perspective in a
single message**. Each simulates a researcher↔expert conversation: ask its top question →
web-search/fetch → emit one atomic evidence note per discrete claim → inspect gaps → ask up to 2
follow-ups → repeat retrieval. Each returns `{perspective_id, conversation[], evidence_notes[],
open_questions[]}` where an evidence note is `{claim, source_url, source_title, snippet,
date_if_available, perspective, confidence(high|medium|low), contested(bool)}`. Then **you**:
flatten all notes, dedupe by normalized `source_url` into a canonical `sources[]` table with ids
`S1..Sn`, stamp each note with its `source_id`, and write `evidence_notes.json` (flat note array)
and `conversations.json` (the traces). See `references/source-policy.md` for the dedupe/normalize rules.

**4 — Outline (naive → refined).** Draft a **naive** outline from prior knowledge only, then a
**refined** outline grounded in a compact digest of the evidence pool. The refined outline is
authoritative: every section must map to ≥1 perspective and to candidate `source_ids`; flag
thin-evidence sections. Node shape: `{heading, level, intent, perspectives[], source_ids[],
evidence_strength(strong|moderate|thin), children[]}`. Write `outline.md` (both outlines; mark the
refined one AUTHORITATIVE). This is the cheapest place to let the user intervene — offer it.

**5 — Draft fan-out (parallel).** For each refined section, spawn a `general-purpose` subagent given
**only its evidence slice** (the notes whose `source_id`/perspective match). Each writes the section
with inline `[S#]` markers, surfaces disagreement when notes are `contested`, writes briefly and says
so when evidence is thin, and never states a source-specific fact without a marker. Returns
`{heading, markdown, citations_used[], uncertainty_notes[]}`. Assemble sections in outline order.
(For ≤2 sections you may draft inline instead of spawning.)

**6 — Polish.** Add a lead/summary; remove duplication across sections; smooth transitions; verify
`[S#]` markers are consistent; compile an **"Open Questions & Uncertainty"** section from all
`uncertainty_notes` + per-perspective `open_questions`. Add **no** new facts or citations. Write
`report.md` (body + a footnote citation list rendered from `sources`) and `sources.md`
(`S-id | title | url | date`).

**7 — Citation audit.** Run the audit script in this skill's directory:
`python3 scripts/audit_citations.py --report ./storm_runs/<slug>/report.md
--evidence ./storm_runs/<slug>/evidence_notes.json --sources ./storm_runs/<slug>/sources.md
--out ./storm_runs/<slug>/citation_audit.md`. **Non-zero exit** = dangling/ungrounded citations or
coverage below threshold → read `citation_audit.md`, fix (inline or a small repair subagent round),
and re-run. Cap at **2 repair passes**; if it still fails, report the remaining issues honestly.

**8 — Present.** Lead with the report's summary. List the artifact paths. Surface the Open Questions
section verbatim. Report audit status (claims scanned, sources cited, coverage %, any flags).
`SendUserFile` the `report.md`. Offer follow-ups (expand a section, add a perspective, tighten scope).

## Output artifacts (`./storm_runs/<slug>/`)

`research_brief.md` · `perspectives.md` · `evidence_notes.json` · `conversations.json` ·
`outline.md` · `report.md` · `sources.md` · `citation_audit.md`

## Guardrails

- **No fabrication.** Never cite a URL a subagent did not fetch; drop notes for paywalled/404 pages.
  If evidence is thin, narrow scope, lower confidence, and say so — do not pad.
- **Web tools required.** If WebSearch/WebFetch are unavailable, stop and tell the user rather than
  writing from prior knowledge alone.
- **Balance is a deliverable.** A run is not done until every discovered perspective appears in ≥1
  section; present contested claims *as* contested.
- **Stay the orchestrator.** Keep raw pages in subagents; only structured notes return to you.
