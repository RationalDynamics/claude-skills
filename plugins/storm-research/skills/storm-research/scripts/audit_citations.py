#!/usr/bin/env python3
"""Deterministic citation audit for storm-research reports.

Cross-checks a generated report against its evidence pool and canonical source
table. Stdlib only; no network, no LLM.

Checks
------
ERROR  dangling citation     a [S#] marker with no matching row in sources.md
ERROR  ungrounded citation   a cited source has zero supporting evidence notes
ERROR  low claim coverage     fraction of factual sentences carrying a marker < --min-coverage
WARN   unused source         a source in sources.md never cited in the report body
WARN   uncited factual sent. a factual-looking sentence with no citation marker
WARN   source overuse        one source backs > --overuse of all citation occurrences
WARN   contested not shown   a contested cited claim whose sentences show no contrast cue

Exit code
---------
0  no ERRORs and claim coverage >= --min-coverage
1  any ERROR (dangling / ungrounded / coverage below threshold)
2  bad inputs (missing/unreadable file)

The citation/coverage scan covers only the report body *above* the final
References/Sources heading. See references/output-contracts.md for the exact
file formats this script expects.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MARKER_RE = re.compile(r"\[S(\d+)\]")
SOURCE_ROW_RE = re.compile(r"^\s*\|\s*(S\d+)\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# Sections that legitimately contain unsourced statements -> excluded from the claim scan.
EXCLUDED_HEADING_RE = re.compile(
    r"^#{1,6}\s+.*\b(references|sources|bibliography|open questions|uncertaint\w*|"
    r"further research|limitations?|see also|appendix|notes)\b",
    re.I,
)

YEAR_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
CLAIM_VERB_RE = re.compile(
    r"\b(found|finds|reported|reports|showed|shows|estimate[ds]?|estimates|announced|"
    r"announces|according to|stated|states|claim|claims|claimed|concluded|concludes|"
    r"demonstrate[ds]?|demonstrates|revealed|reveals|discovered|discovers|determined|"
    r"determines|measured|measures|published|publishes|ranked|ranks|rose|fell|increased|"
    r"increases|decreased|decreases|grew|grown|declined|declines|surged|plunged|doubled|"
    r"tripled|founded|launched|acquired|reaches?|reached)\b",
    re.I,
)
PROPER_RUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+")
CONTRAST_RE = re.compile(
    r"\b(however|whereas|but|although|though|while|despite|in contrast|on the other hand|"
    r"conversely|critics?|disput\w+|disagree\w*|contested|contend\w*|debate\w*|"
    r"controvers\w+|some argue|others)\b",
    re.I,
)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def sid_key(s):
    return int(s[1:])


def die(msg, code=2):
    print(f"audit_citations: {msg}", file=sys.stderr)
    sys.exit(code)


def read_text(path):
    p = Path(path)
    if not p.is_file():
        die(f"file not found: {path}")
    return p.read_text(encoding="utf-8")


def build_body(text):
    """Return [(lineno, line)] for the claim-bearing body: drops fenced code blocks
    and whole sections whose heading is a meta section (References, Open Questions,
    Uncertainty, ...) including their subsections."""
    body, in_code, skip_level = [], False, None
    for i, ln in enumerate(text.splitlines()):
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        hm = HEADING_RE.match(ln)
        if hm:
            level = len(hm.group(1))
            if skip_level is not None and level <= skip_level:
                skip_level = None  # back out to a sibling/higher heading
            if EXCLUDED_HEADING_RE.match(ln):
                skip_level = level
                continue
            if skip_level is not None:
                continue
            body.append((i + 1, ln))
            continue
        if skip_level is not None:
            continue
        body.append((i + 1, ln))
    return body


ABBREV = ["U.S.A.", "U.S.", "U.K.", "e.g.", "i.e.", "etc.", "vs.", "Mr.", "Mrs.",
          "Ms.", "Dr.", "St.", "No.", "Inc.", "Co.", "Ltd.", "Fig.", "cf.", "al.",
          "Jr.", "Sr.", "approx."]


def _protect(text):
    """Hide periods that don't end sentences (abbreviations, single initials) so the
    splitter doesn't break on them."""
    for a in ABBREV:
        text = text.replace(a, a.replace(".", "\x00"))
    return re.sub(r"\b([A-Za-z])\.", lambda m: m.group(1) + "\x00", text)  # initials like "J. K."


def _split_sentences(text):
    return [s.replace("\x00", ".").strip()
            for s in SENT_SPLIT_RE.split(_protect(text.strip())) if s.strip()]


def extract_sentences(body):
    """Reflow wrapped prose into paragraphs, then split into (start_lineno, sentence).
    Real reports hard-wrap lines, so sentences must be reassembled before splitting or
    a citation marker on the next physical line looks 'missing'."""
    out, para, start = [], [], None
    for lineno, line in body:
        s = line.strip()
        list_m = re.match(r"^(?:[-*+]\s+|\d+\.\s+)(.*)$", s) if s else None
        if not s or s.startswith("#") or s.startswith("|") or list_m is not None:
            if para:
                out += [(start, x) for x in _split_sentences(" ".join(para))]
                para = []
            if list_m is not None:
                out += [(lineno, x) for x in _split_sentences(list_m.group(1))]
            start = None
            continue
        if not para:
            start = lineno
        para.append(s)
    if para:
        out += [(start, x) for x in _split_sentences(" ".join(para))]
    return out


def is_factual(sentence_without_markers):
    s = sentence_without_markers
    if len(s.split()) < 5:
        return False
    return bool(
        YEAR_RE.search(s)
        or CLAIM_VERB_RE.search(s)
        or PROPER_RUN_RE.search(s)
        or NUM_RE.search(s)
    )


def parse_sources(text):
    ids = []
    for ln in text.splitlines():
        m = SOURCE_ROW_RE.match(ln)
        if m:
            ids.append(m.group(1))
    return set(ids)


def parse_evidence(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"evidence file is not valid JSON: {e}")
    if isinstance(data, dict):  # tolerate {"notes": [...]}
        data = data.get("notes") or data.get("evidence_notes") or []
    if not isinstance(data, list):
        die("evidence JSON must be a list of notes (or {notes:[...]})")
    grounded = {n.get("source_id") for n in data if isinstance(n, dict) and n.get("source_id")}
    contested = {
        n.get("source_id")
        for n in data
        if isinstance(n, dict) and n.get("contested") and n.get("source_id")
    }
    return data, grounded, contested


def main():
    ap = argparse.ArgumentParser(
        description="Deterministic citation audit for a storm-research report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--report", required=True, help="path to report.md")
    ap.add_argument("--evidence", required=True, help="path to evidence_notes.json (flat array)")
    ap.add_argument("--sources", required=True, help="path to sources.md (S-id table)")
    ap.add_argument("--out", help="path to write citation_audit.md (default: stdout only)")
    ap.add_argument("--overuse", type=float, default=0.35, help="max fraction one source may back")
    ap.add_argument("--min-coverage", type=float, default=0.90, help="min claim coverage to pass")
    args = ap.parse_args()

    report = read_text(args.report)
    sources_set = parse_sources(read_text(args.sources))
    notes, grounded_ids, contested_ids = parse_evidence(read_text(args.evidence))

    body = build_body(report)
    body_text = "\n".join(line for _, line in body)
    occ = Counter("S" + d for d in MARKER_RE.findall(body_text))
    cited_ids = set(occ)
    total_occ = sum(occ.values())

    # coverage + uncited factual sentences
    sentences = extract_sentences(body)
    factual_total = factual_with = 0
    uncited = []
    for lineno, sent in sentences:
        if sent.rstrip().endswith("?"):
            continue  # questions are not factual claims
        nomark = MARKER_RE.sub("", sent)
        if is_factual(nomark):
            factual_total += 1
            if MARKER_RE.search(sent):
                factual_with += 1
            else:
                uncited.append((lineno, sent))
    claim_cov = factual_with / factual_total if factual_total else 1.0
    source_cov = (
        len(cited_ids & sources_set) / len(sources_set) if sources_set else 1.0
    )

    # error conditions
    dangling = sorted(cited_ids - sources_set, key=sid_key)
    ungrounded = sorted((cited_ids & sources_set) - grounded_ids, key=sid_key)
    coverage_fail = claim_cov < args.min_coverage

    # warnings
    unused = sorted(sources_set - cited_ids, key=sid_key)
    overused = sorted(
        ((cid, occ[cid]) for cid in occ if total_occ and occ[cid] / total_occ > args.overuse),
        key=lambda t: -t[1],
    )
    contested_unshown = []
    for cid in sorted(contested_ids & cited_ids, key=sid_key):
        tag = f"[{cid}]"
        sents = [s for _, s in sentences if tag in s]
        if sents and not any(CONTRAST_RE.search(s) for s in sents):
            contested_unshown.append(cid)

    errors = []
    if dangling:
        errors.append(f"Dangling citations (no row in sources.md): {', '.join(dangling)}")
    if ungrounded:
        errors.append(
            f"Ungrounded citations (no supporting evidence note): {', '.join(ungrounded)}"
        )
    if coverage_fail:
        errors.append(
            f"Claim coverage {claim_cov:.0%} below threshold {args.min_coverage:.0%}"
        )

    # build report
    lines = []
    verdict = "PASS" if not errors else "FAIL"
    lines.append("# Citation audit")
    lines.append("")
    lines.append(f"**Report:** `{args.report}`  ")
    lines.append(f"**Verdict:** {verdict}")
    lines.append("")
    lines.append("## Stats")
    lines.append(f"- Factual sentences scanned: {factual_total}")
    lines.append(f"- Sentences with a citation: {factual_with}")
    lines.append(f"- Claim coverage: {claim_cov:.0%} (threshold {args.min_coverage:.0%})")
    lines.append(
        f"- Sources total / cited / unused: {len(sources_set)} / "
        f"{len(cited_ids & sources_set)} / {len(unused)}"
    )
    lines.append(f"- Source coverage: {source_cov:.0%}")
    lines.append(f"- Total citation occurrences: {total_occ}")
    lines.append("")
    lines.append("## Errors")
    lines.extend([f"- {e}" for e in errors] or ["- None."])
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    lines.append(f"### Uncited factual sentences ({len(uncited)})")
    if uncited:
        lines.extend([f"- L{ln}: {s}" for ln, s in uncited[:50]])
        if len(uncited) > 50:
            lines.append(f"- ...and {len(uncited) - 50} more")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append(f"### Unused sources ({len(unused)})")
    lines.append("- " + (", ".join(unused) if unused else "None."))
    lines.append("")
    lines.append("### Source overuse")
    if overused:
        lines.extend(
            [f"- {cid} backs {c}/{total_occ} ({c / total_occ:.0%} > {args.overuse:.0%})"
             for cid, c in overused]
        )
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("### Contested claims not presented as contested")
    lines.append("- " + (", ".join(contested_unshown) if contested_unshown else "None."))
    lines.append("")
    lines.append("## Verdict")
    if errors:
        lines.append(f"FAIL — {len(errors)} error(s). Fix and re-run.")
    else:
        lines.append(f"PASS — no errors; claim coverage {claim_cov:.0%}.")
    report_md = "\n".join(lines) + "\n"

    if args.out:
        Path(args.out).write_text(report_md, encoding="utf-8")

    # terse stdout summary
    print(
        f"[{verdict}] coverage={claim_cov:.0%} sources_cited={len(cited_ids & sources_set)}/"
        f"{len(sources_set)} errors={len(errors)} "
        f"warnings={len(uncited) + len(unused) + len(overused) + len(contested_unshown)}"
    )
    for e in errors:
        print(f"  ERROR: {e}")
    if args.out:
        print(f"  wrote {args.out}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
