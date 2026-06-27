---
name: session-cost
description: >-
  Report token usage, wall-clock time, and (illustrative) cost for Claude Code
  sessions by parsing the on-disk JSONL transcripts under ~/.claude/projects.
  Use when asked "how much did this session cost", "token usage", "cost
  breakdown", "compare two runs / sessions", "cost by worktree", or to audit
  spend outside a session (the /cost command is CLI-only and unavailable in the
  desktop app). Dedups streamed/re-serialized records and prices per model, so
  totals reconcile with `ccusage`. Read-only — touches no project files.
---

# session-cost — offline token / time / cost for Claude Code

## What this is

A small Python tool ([scripts/cc_session_cost.py](scripts/cc_session_cost.py))
that reads the transcripts Claude Code writes to disk and reports, per session
or per worktree: assistant turns, tool calls, input / cache-write / cache-read /
output tokens, wall-clock span, and an estimated dollar cost.

It exists because `/cost` is only available in the terminal CLI (not the desktop
app), and because naive token-summing over the JSONL **massively overcounts**.

## Where the data lives

Claude Code (CLI **and** desktop) persists every session to:

- `~/.claude/projects/<project-slug>/<session-id>.jsonl` — the main transcript
- `~/.claude/projects/<project-slug>/<session-id>/**.jsonl` — subagent + workflow transcripts

The `<project-slug>` is the working directory with `/` → `-`, so **each git
worktree is its own project dir** — that's how "by worktree" grouping works.
Each assistant turn carries a `message.usage` block (`input_tokens`,
`cache_creation_input_tokens` split into `ephemeral_5m`/`ephemeral_1h`,
`cache_read_input_tokens`, `output_tokens`), plus `model` and `timestamp`. There
is no dollar field — cost is computed from the editable `PRICES` table.

## Usage

Run the bundled script directly with `python3` (no dependencies beyond the
standard library). `SKILL_DIR` is this skill's own directory — when installed via
the marketplace it's the plugin's `skills/session-cost/`; for a symlink install
it's `~/.claude/skills/session-cost/`:

```sh
python3 "$SKILL_DIR/scripts/cc_session_cost.py" --list                 # sessions, newest first
python3 "$SKILL_DIR/scripts/cc_session_cost.py" --by-worktree          # every worktree, totalled
python3 "$SKILL_DIR/scripts/cc_session_cost.py" --by-worktree curie chaum   # only matching worktrees
python3 "$SKILL_DIR/scripts/cc_session_cost.py" <session-id>           # full per-session report
python3 "$SKILL_DIR/scripts/cc_session_cost.py" <id-a> <id-b>          # side-by-side comparison
```

`--by-worktree` filters are case-insensitive substrings matched against the
project-slug, so a worktree name fragment selects it. To find a session id, run
`--list` and match on date + title.

## How it stays trustworthy (the two bugs to never reintroduce)

1. **Dedup, keep-max.** Claude Code re-serializes each assistant message many
   times. The main loop writes identical final-usage copies; subagents/workflows
   write **streaming partials** whose `output_tokens` grow across copies
   (`1 → 3 → 265`). The tool keys on `(message.id, requestId)` and keeps the
   record with the **maximum** `output_tokens` (the final one). Summing raw
   records overcounts ~2–3×; keeping the *first* partial undercounts. This
   matches `ccusage`'s message-id dedup.

2. **Per-model pricing.** A session/day often mixes opus + sonnet + haiku, and
   cache-read tokens dominate volume, so pricing everything at Opus rates
   overstates cost. `PRICES` is keyed by model family (substring match on the
   model id) and cost is summed per family.

After both fixes, totals reconcile with `npx ccusage@latest` to within
live-session drift.

## Pricing (edit `PRICES` to your contract)

Rates are **illustrative current published $/1M tokens**; token counts are exact
regardless. Cache-write 5m = 1.25× input, cache-write 1h = 2× input, cache-read
= 0.1× input.

| family | input | output | cw5m | cw1h | cache-read |
|---|--:|--:|--:|--:|--:|
| opus (`claude-opus-4-8`) | 5 | 25 | 6.25 | 10 | 0.50 |
| sonnet (`claude-sonnet-4-6`) | 3 | 15 | 3.75 | 6 | 0.30 |
| haiku (`claude-haiku-4-5`) | 1 | 5 | 1.25 | 2 | 0.10 |

> Note vs ccusage: this tool prices 1-hour cache-writes at the true **2×** rate;
> `ccusage`/LiteLLM often price *all* cache-creation at the 5-min 1.25× rate, so
> heavy 1h-cache sessions read slightly higher here. Align the `cw1h` row to
> match ccusage exactly if you need byte-for-byte agreement.

## Reading the numbers

- **cache-read dominates.** Long sessions re-read accumulated context every turn;
  at 0.1× it's still usually the largest single cost line. `input (fresh)` is
  only the uncached remainder.
- **Wall-clock = first→last timestamp**, so it includes idle/think time, not
  just compute. A workflow that ran concurrently shows its own shorter span; the
  session total stays the elapsed wall-clock.
- **Live sessions keep growing** — a report on the *current* session rises every
  turn. Snapshot after sessions close for a stable comparison.
- **Cross-check:** `npx ccusage@latest` parses the same JSONL (daily/session
  views) and is a good independent sanity check on token totals.

## Extending

- Add a model family: add a `PRICES` row (the key is matched as a substring of
  the model id, e.g. `"opus"` matches `claude-opus-4-8`).
- The default `DEFAULT_FAMILY` (opus) prices any unrecognized model — change it
  if your default tier differs.
