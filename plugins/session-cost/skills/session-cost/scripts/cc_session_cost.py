#!/usr/bin/env python3
"""Offline token / time / cost report for Claude Code, from the on-disk JSONL.

Claude Code (CLI and desktop) writes every session to
  ~/.claude/projects/<project-slug>/<session-id>.jsonl
plus a sibling <session-id>/ folder holding subagent + workflow transcripts.
The <project-slug> is the working directory with '/'->'-', so each git
worktree is its own project dir — which is how we group "by worktree".

Dedup (the part that makes the numbers trustworthy):
  Claude Code re-serializes the same assistant message many times. The main
  loop writes identical final-usage copies; subagents/workflows write STREAMING
  PARTIALS whose output grows across copies (1 -> 3 -> 265 ...). So we key on
  (message.id, requestId) and keep the record with the MAX output_tokens — the
  final, complete one. Summing raw records double-counts (2-3x); keeping the
  first partial under-counts. This matches `ccusage`'s message-id dedup.

Token counts are then exact; only the $ depends on the (editable) PRICES table.

Usage:
  python3 cc_session_cost.py --list                       # sessions, newest first
  python3 cc_session_cost.py --by-worktree                # every worktree, totalled
  python3 cc_session_cost.py --by-worktree curie chaum    # only matching worktrees
  python3 cc_session_cost.py <session-id> [<session-id>]  # one, or compare several
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

PROJECTS = os.path.expanduser("~/.claude/projects")

# $ per 1M tokens, PER MODEL FAMILY (matched by substring on the model id).
# Pricing must be model-aware: a session/day often mixes opus + sonnet + haiku,
# and cache-read tokens dominate volume, so pricing everything at Opus rates
# overstates cost 2-4x. Edit to your contract; align to LiteLLM to match ccusage.
# Current published rates (per 1M tokens). cache-write 5m = 1.25x input,
# cache-write 1h = 2x input, cache-read = 0.1x input.
PRICES = {
    "opus":   {"input": 5.0, "output": 25.0, "cw5": 6.25, "cw1h": 10.0, "cache_read": 0.50},
    "sonnet": {"input": 3.0, "output": 15.0, "cw5": 3.75, "cw1h": 6.0,  "cache_read": 0.30},
    "haiku":  {"input": 1.0, "output": 5.0,  "cw5": 1.25, "cw1h": 2.0,  "cache_read": 0.10},
}
DEFAULT_FAMILY = "opus"

SUMFIELDS = ("turns", "input", "output", "cache_read", "cw5", "cw1h", "tool_uses")


def _family(model):
    m = (model or "").lower()
    for fam in PRICES:
        if fam in m:
            return fam
    return DEFAULT_FAMILY


def _records(path):
    try:
        fh = open(path, encoding="utf-8")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _ts(rec):
    t = rec.get("timestamp")
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def collect(path, store, span):
    """Fold one transcript into `store` (key -> best record), keeping the
    MAX-output copy per (message.id, requestId). `span` is a [first, last]
    list updated in place. `store` is shared across every file in the unit
    so a message repeated within or across files is counted once."""
    for rec in _records(path):
        ts = _ts(rec)
        if ts:
            if span[0] is None or ts < span[0]:
                span[0] = ts
            if span[1] is None or ts > span[1]:
                span[1] = ts
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        u = msg.get("usage")
        if not u:
            continue
        mid = msg.get("id")
        key = (mid, rec.get("requestId")) if mid else ("uuid", rec.get("uuid"))
        out = u.get("output_tokens", 0)
        cur = store.get(key)
        if cur is not None and out <= cur["output"]:
            continue  # keep the larger (final) partial
        cw = u.get("cache_creation") or {}
        tool_uses = sum(
            1
            for b in (msg.get("content") or [])
            if isinstance(b, dict) and b.get("type") == "tool_use"
        )
        store[key] = dict(
            output=out,
            input=u.get("input_tokens", 0),
            cache_read=u.get("cache_read_input_tokens", 0),
            cw5=cw.get("ephemeral_5m_input_tokens", 0),
            cw1h=cw.get("ephemeral_1h_input_tokens", 0),
            model=msg.get("model", "?"),
            tool_uses=tool_uses,
        )


def finalize(store, span):
    a = {k: 0 for k in SUMFIELDS}
    a["first"], a["last"] = span[0], span[1]
    a["models"] = defaultdict(int)
    a["by_fam"] = defaultdict(lambda: {k: 0 for k in ("input", "output", "cache_read", "cw5", "cw1h")})
    for v in store.values():
        a["turns"] += 1
        a["tool_uses"] += v["tool_uses"]
        a["models"][v["model"]] += 1
        fam = a["by_fam"][_family(v["model"])]
        for k in ("input", "output", "cache_read", "cw5", "cw1h"):
            a[k] += v[k]
            fam[k] += v[k]
    return a


def cost(a):
    total = 0.0
    for famname, toks in a.get("by_fam", {}).items():
        p = PRICES.get(famname, PRICES[DEFAULT_FAMILY])
        total += (
            toks["input"] / 1e6 * p["input"]
            + toks["output"] / 1e6 * p["output"]
            + toks["cache_read"] / 1e6 * p["cache_read"]
            + toks["cw5"] / 1e6 * p["cw5"]
            + toks["cw1h"] / 1e6 * p["cw1h"]
        )
    return total


def minutes(a):
    if a["first"] and a["last"]:
        return (a["last"] - a["first"]).total_seconds() / 60
    return 0.0


def session_files(main_jsonl):
    sub = main_jsonl[:-6]
    files = [main_jsonl]
    if os.path.isdir(sub):
        files += sorted(glob.glob(os.path.join(sub, "**", "*.jsonl"), recursive=True))
    return files


def worktree_label(slug):
    marker = "-claude-worktrees-"
    return slug.split(marker, 1)[1] if marker in slug else slug


def print_block(a, label):
    print(f"\n## {label}")
    print(f"  assistant turns : {a['turns']:,}")
    print(f"  tool calls      : {a['tool_uses']:,}")
    print(f"  input (fresh)   : {a['input']:,}")
    print(f"  cache write 5m  : {a['cw5']:,}")
    print(f"  cache write 1h  : {a['cw1h']:,}")
    print(f"  cache read      : {a['cache_read']:,}")
    print(f"  output          : {a['output']:,}")
    print(f"  wall-clock      : {minutes(a):.1f} min")
    print(f"  est cost        : ${cost(a):,.2f}   (illustrative; edit PRICES)")


def resolve(arg):
    if arg.endswith(".jsonl") and os.path.exists(arg):
        return arg
    hits = glob.glob(os.path.join(PROJECTS, "*", f"{arg}.jsonl"))
    if not hits:
        sys.exit(f"no transcript for {arg!r} under {PROJECTS}")
    return hits[0]


def cmd_session(arg):
    main = resolve(arg)
    span = [None, None]
    main_store, sub_store = {}, {}
    collect(main, main_store, span)
    for f in session_files(main)[1:]:
        collect(f, sub_store, span)
    main_agg = finalize(main_store, span)
    sub_agg = finalize(sub_store, span)
    total_store = dict(main_store)
    total_store.update(sub_store)
    total = finalize(total_store, span)
    print("=" * 60)
    print(f"SESSION {os.path.basename(main)[:-6]}")
    print(f"  worktree: {worktree_label(os.path.basename(os.path.dirname(main)))}")
    print_block(main_agg, "Main loop")
    if sub_agg["turns"]:
        print_block(sub_agg, "Subagents / workflows")
    print_block(total, "TOTAL (deduped)")
    return total


def cmd_by_worktree(filters):
    rows = []
    grand_store, grand_span = {}, [None, None]
    for proj in sorted(glob.glob(os.path.join(PROJECTS, "*"))):
        if not os.path.isdir(proj):
            continue
        slug = os.path.basename(proj)
        if filters and not any(f.lower() in slug.lower() for f in filters):
            continue
        sessions = sorted(glob.glob(os.path.join(proj, "*.jsonl")))
        if not sessions:
            continue
        store, span = {}, [None, None]
        for s in sessions:
            for f in session_files(s):
                collect(f, store, span)
                collect(f, grand_store, grand_span)
        a = finalize(store, span)
        a["sessions"] = len(sessions)
        rows.append((worktree_label(slug), a))
    rows.sort(key=lambda r: cost(r[1]), reverse=True)
    grand = finalize(grand_store, grand_span)
    w = 42
    print("=" * (w + 56))
    print(f"{'WORKTREE':{w}} {'sess':>4} {'turns':>6} {'output':>10} "
          f"{'cacheRead':>12} {'min':>5} {'cost$':>9}")
    print("-" * (w + 56))
    for label, a in rows:
        print(f"{label[:w]:{w}} {a['sessions']:>4} {a['turns']:>6} {a['output']:>10,} "
              f"{a['cache_read']:>12,} {minutes(a):>5.0f} {cost(a):>9,.2f}")
    print("-" * (w + 56))
    print(f"{'TOTAL (' + str(len(rows)) + ' worktrees, deduped)':{w}} {'':>4} "
          f"{grand['turns']:>6} {grand['output']:>10,} {grand['cache_read']:>12,} "
          f"{'':>5} {cost(grand):>9,.2f}")
    print("\nToken counts exact & deduped (keep-max per message). $ via editable PRICES.")


def cmd_list():
    rows = []
    for f in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        last, title = None, ""
        for rec in _records(f):
            t = _ts(rec)
            if t and (last is None or t > last):
                last = t
            title = rec.get("aiTitle") or rec.get("customTitle") or title
        rows.append((last, os.path.basename(f)[:-6],
                     worktree_label(os.path.basename(os.path.dirname(f))), title))
    rows.sort(key=lambda r: (r[0] is None, r[0]), reverse=True)
    for last, sid, wt, title in rows[:40]:
        when = last.strftime("%Y-%m-%d %H:%M") if last else "?"
        print(f"{when}  {sid}  [{wt[:26]:26}]  {title[:44]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
    elif args[0] == "--list":
        cmd_list()
    elif args[0] == "--by-worktree":
        cmd_by_worktree(args[1:])
    elif len(args) == 1:
        cmd_session(args[0])
    else:
        totals = [(a, cmd_session(a)) for a in args]
        print("\n" + "=" * 60 + "\nCOMPARISON (deduped)")
        for a, t in totals:
            print(f"  {a[:20]:20} out={t['output']:>9,}  ${cost(t):>8,.2f}  {minutes(t):>5.0f} min")
