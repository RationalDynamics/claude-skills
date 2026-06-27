# Source policy

Rules for gathering, deduping, and citing sources. The drafting prompts and
`scripts/audit_citations.py` both depend on the thresholds here — keep them in sync.

## Source hierarchy (prefer higher tiers)

1. **Primary / authoritative** — peer-reviewed papers, official standards, primary datasets,
   regulatory filings, original reporting, first-party documentation, court records.
2. **Reputable secondary** — established news outlets, textbooks, review articles, encyclopedias
   with citations, recognized industry analysts.
3. **Tertiary / informal** — blogs, forums, marketing pages, unsigned web copy. Use only to
   *locate* primary sources or for clearly-attributed opinion; never as the sole support for a
   factual claim.

When tiers disagree, the higher tier wins and the lower-tier claim becomes context, not fact.

## Never cite what you didn't fetch

A claim may be cited **only** if a subagent actually fetched the page and extracted a supporting
snippet. Search-result titles/snippets alone are **not** sufficient grounding — open the page.
Drop any claim whose source 404s, is paywalled past the relevant content, or doesn't actually say
what the claim asserts.

## Recency

If the brief sets a `timeframe`/recency need, prefer sources dated within it and record
`date_if_available` on every note. For fast-moving topics, flag claims that rest on sources older
than the cutoff as `confidence: low` or `contested` so the audit and the reader can see the risk.

## Dedupe & canonical source ids

After the research fan-out, the main agent builds the canonical `sources[]` table:

- **Normalize** each URL before comparing: lowercase scheme+host, strip `www.`, drop tracking
  params (`utm_*`, `fbclid`, `gclid`, `ref`, …), strip fragments (`#...`), strip trailing slash.
- One canonical source per normalized URL; assign ids `S1, S2, …` in first-seen order.
- Stamp every evidence note with its `source_id`. Two notes from the same page share one id.
- Keep the richest title/date seen for that URL.

## Disagreement

Do not resolve genuine disagreement by averaging or omission. When sources conflict, keep both
notes, set `contested: true`, and ensure the drafted section presents the disagreement
("A finds X, whereas B reports Y"). The audit flags contested claims whose section text shows no
sign of contrast.

## Source concentration (overuse)

A report leaning on one source is fragile. Flag (WARN) when any single source backs **more than 35%**
of all cited claim-occurrences (`--overuse 0.35`, tunable). Mitigate by finding corroborating or
opposing sources for the over-represented claims, not by deleting citations.

## Coverage targets

- **Claim coverage** — fraction of factual-looking sentences that carry a citation marker. Target
  ≥ 0.90 (`--min-coverage`). Below that fails the audit.
- **Source coverage** — fraction of gathered sources actually cited. Low source coverage is a WARN,
  not a failure (some gathered sources legitimately don't make the final cut).
