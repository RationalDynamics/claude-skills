# Output contracts — schemas & artifact formats

Subagent return shapes and on-disk file formats. The section-drafting subagents, the main agent,
and `scripts/audit_citations.py` all depend on these being exact. When in doubt, match this file
byte-for-byte.

## Subagent return schemas

**Perspective** (from perspective discovery)
```json
{ "id": "p1-economist", "name": "Labor economist",
  "focus": "wage and employment effects",
  "rationale": "why this lens matters for the topic",
  "key_questions": ["...", "...", "..."] }
```

**Research result** (one per perspective, from the research fan-out)
```json
{ "perspective_id": "p1-economist",
  "conversation": [{"role":"writer","text":"...","queries":["..."]},
                   {"role":"expert","text":"...","queries":["..."]}],
  "evidence_notes": [ <EvidenceNote without id/source_id; main agent assigns those> ],
  "open_questions": ["unresolved question", "..."] }
```

**EvidenceNote** (atomic; one claim each)
```json
{ "claim": "single atomic factual claim",
  "source_url": "https://...", "source_title": "Page title",
  "snippet": "supporting quote or close paraphrase from the fetched page",
  "date_if_available": "YYYY-MM-DD or \"\"",
  "perspective": "p1-economist",
  "confidence": "high|medium|low", "contested": false }
```

**OutlineNode** (recursive)
```json
{ "heading": "Economic effects", "level": 1,
  "intent": "what this section covers",
  "perspectives": ["p1-economist","p3-policy"],
  "source_ids": ["S2","S5","S9"],
  "evidence_strength": "strong|moderate|thin",
  "children": [ <OutlineNode>, ... ] }
```
`level` 1 = top-level section (`##`), 2 = subsection (`###`).

**Section** (one per section, from the draft fan-out)
```json
{ "heading": "Economic effects",
  "markdown": "## Economic effects\n\nText with inline [S2] markers...",
  "citations_used": ["S2","S5"],
  "uncertainty_notes": ["weak/contested/unverifiable points"] }
```

## On-disk artifacts (`./storm_runs/<slug>/`)

### `research_brief.md`
Human-readable brief: topic, angle, audience, depth, timeframe, must-cover, exclusions,
target sections/words. One short section per field.

### `perspectives.md`
A table or list of the discovered perspectives: name, focus, rationale, key questions.

### `evidence_notes.json`  ← consumed by the audit
A **flat JSON array** of evidence notes, each stamped by the main agent with `id` (`N1..`) and
`source_id` (`S1..`):
```json
[
  { "id": "N1", "source_id": "S1",
    "claim": "...", "source_url": "...", "source_title": "...",
    "snippet": "...", "date_if_available": "2024-03-01",
    "perspective": "p1-economist", "confidence": "high", "contested": false }
]
```
The audit only requires `source_id` on each note (plus `claim`, `contested` for richer checks);
extra fields are fine.

### `conversations.json`
A JSON array of the per-perspective `{perspective_id, conversation[]}` traces (the research dialogue,
kept separate from the flat note array for a clean audit contract).

### `outline.md`
Two sections — `## Naive outline` and `## Refined outline (AUTHORITATIVE)` — each rendered as a
nested markdown list. Annotate refined nodes with their perspectives and `evidence_strength`, e.g.
`- Economic effects — [p1,p3] (strong)`.

### `report.md`  ← consumed by the audit
```markdown
# <Title>

<lead / summary paragraph(s)>

## <Section heading>
Prose with inline citation markers like [S2] and [S5]. ...

## Open Questions & Uncertainty
- ...

## References
S1. <title> — <url> (<date>)
S2. <title> — <url> (<date>)
```
Rules the audit relies on:
- In-body citations use **bracketed** markers `[S#]`.
- The references list uses **un-bracketed** `S1.` entries, and lives under a final heading whose
  title contains "References" or "Sources". The audit splits there: citation/coverage checks scan
  only the body **above** that heading.

### `sources.md`  ← consumed by the audit
A markdown table; the audit reads the canonical id set from the first column.
```markdown
| id | title | url | date |
|----|-------|-----|------|
| S1 | <title> | https://... | 2024-03-01 |
| S2 | <title> | https://... |  |
```

### `citation_audit.md`
Written by the audit script. ERRORS / WARNINGS / VERDICT + run stats. See `audit_citations.py`.
