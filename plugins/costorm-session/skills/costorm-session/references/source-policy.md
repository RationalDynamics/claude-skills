# Co-STORM source and citation policy

Keep every research turn and the final report grounded in pages that were actually opened.

## Source selection

Prefer primary and authoritative sources: peer-reviewed papers, official documentation and data,
standards, regulatory records, and original reporting. Use reputable secondary sources for context
or synthesis. Use informal and promotional sources only to locate stronger evidence or when their
point of view is itself relevant.

## Grounding contract

- Search-result snippets are discovery aids, not evidence. Open the page before using it.
- Store one atomic factual claim per claim record with at least one source anchor containing URL,
  title, and a supporting quote or close paraphrase.
- Drop sources that are inaccessible, paywalled beyond the relevant passage, or do not support the
  claim attributed to them.
- Preserve disagreement as separate claims and contradiction nodes. Do not average conflicting
  evidence into false consensus.

## Source identity and dedupe

Normalize URLs before assigning source IDs: lowercase scheme and host, remove `www.`, tracking
parameters and fragments, and strip a trailing slash. Reuse one `s_` ID for the same page and merge
its supporting anchors rather than creating duplicates.

## Final report citations

Draft only from claims already present in `session_state.json`. Number the canonical sources in
first-citation order and use bracketed markers such as `[1]` in `report.md`; render the same mapping
in `sources.md`. Put a marker on every sentence containing a source-specific factual claim. Present
contradictions with explicit contrast language, keep thin branches brief, and carry unresolved
questions into the final report instead of filling gaps from prior knowledge.
