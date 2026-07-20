---
name: evict
description: >
  One-shot context surgery. Invoke /evict to dump the current session exactly, auto-segment it into
  the distinct things you worked on ("blocks") with no pre-placed markers, then decide per block
  whether to keep it verbatim, keep only a summary, or evict it — and stage a lean /clear reload of
  just what you chose. A standalone, one-shot context compactor — no prior setup or markers needed.
disable-model-invocation: true
---

# Evict

You are a one-shot context-surgery tool. When invoked you: (1) dump the current session **exactly**
to disk, (2) auto-segment the whole conversation-so-far into distinct work **blocks**, (3) let the
user decide per block — **keep verbatim / keep as summary / evict**, and (4) stage a clean `/clear`
reload containing only the kept context.

It needs **no** prior setup or markers — it segments the session itself, in one shot. Default for a
kept block is **verbatim** ("keep it exactly").

## Prerequisites

The post-`/clear` reload is delivered by a `SessionStart` hook. It must be registered in
`~/.claude/settings.json` pointing at this skill's `scripts/reload.sh`:

```json
{ "hooks": { "SessionStart": [ { "hooks": [
  { "type": "command", "command": "~/.claude/skills/evict/scripts/reload.sh" }
] } ] } }
```

If it is not registered, do steps 1–5 anyway but warn the user at step 6 that `/clear` will **not**
auto-reload — they'll need to reopen `evict_reload.md` manually.

## Step 1 — Dump the session exactly

Run the backend dumper. Prefer passing the current **session id**: it is the UUID segment of your
scratchpad directory path (`…/<session-id>/scratchpad`). If you can't determine it, omit the flag —
the script falls back to the newest transcript in the project dir, which is the live session.

```bash
python3 ~/.claude/skills/evict/scripts/dump_session.py --session-id <SESSION_ID>
```

It writes `full-transcript.md`, one `turns/turn-<N>.md` per turn, and `index.json` under an output
directory, and prints a TURN INDEX to stdout. A "turn" = one human prompt plus every assistant/tool
exchange until the next human prompt.

**Capture the `out_dir:` line the script prints and use it verbatim for every path in Steps 4–5.**
The script may fall back to a different session than the id you passed (newest transcript), so its
reported `out_dir` — not a re-derived `<session-id>` — is the single source of truth for where the
turn files live and where the reload file and marker must point. Treat its `out_dir` as `$OUT_DIR`
below.

The script now refuses to write an empty capture: if it exits non-zero (no turns parsed) or reports
`turns: 0`, output **"Nothing to evict — the session has no content yet."** and stop. Do not proceed
to staging on a failed dump.

## Step 2 — Segment turns into blocks

Read the TURN INDEX (and skim `full-transcript.md` / individual `turns/turn-<N>.md` as needed).
Group **contiguous** turns into a handful of semantic **blocks** — each block is one distinct thing
the user worked on (a feature, a tangent, a debugging detour, a review round). A single large turn
can be its own block. Give each block:

- a **number** (1..N, in conversation order),
- a one-line **label**, and
- the **turn range** it covers (e.g. turns 3–5).

Record, for each block, which `turns/turn-<N>.md` files compose it (its verbatim slice) and a
2–4 sentence **summary** you could substitute for it.

## Step 3 — Let the user decide per block

Show the block list first, plainly:

```
Session split into N blocks:

  Block 1  (turns 0–2)   Setting up the parser
  Block 2  (turns 3–4)   Tangent: debugging the CI worker
  Block 3  (turns 5–8)   Back to the parser — segmentation logic
  Block 4  (turns 9–10)  Current working context
```

Then collect a decision **per block**. Default path (**≤ 8 blocks**): use `AskUserQuestion`, one
question per block (batch up to 4 questions per call), each with three options:

- **Keep verbatim** (default) — reload the block's exact text
- **Keep as summary** — reload only your 2–4 sentence summary
- **Evict** — drop it entirely

For a `Keep as summary` pick, show the summary you'll use so the user can adjust it.

**Fallback (> 8 blocks)** to avoid many dialogs: ask as text —
`"Which blocks to KEEP? (e.g. 1,3,4)"`, then of those `"Which to keep as SUMMARY instead of
verbatim? (e.g. 3)"`. Anything kept and not marked summary stays **verbatim**.

If the user signals cancel ("nevermind", "cancel", "stop"), output
**"Evict cancelled. Nothing was staged."** and stop without writing anything.

## Step 4 — Build the reload file

Write `$OUT_DIR/evict_reload.md` (the same `$OUT_DIR` the dumper printed in Step 1 — do not
substitute a re-derived `<session-id>`):

```markdown
# Restored Context (via /evict)

Only the blocks below were kept. Evicted blocks were work the user chose to discard.

---

## Block <N>: <label>  (kept verbatim)

<exact concatenation of the block's turns/turn-<N>.md files>

---

## Block <M>: <label>  (summary)

<your summary of the block>

---
```

For **verbatim** blocks, concatenate the exact `turns/turn-<N>.md` contents — do not paraphrase.
For **summary** blocks, write the summary. Omit evicted blocks entirely.

## Step 5 — Write the pending marker

Write `/tmp/.evict_pending.json`:

```json
{
  "pending": true,
  "work_dir": "$OUT_DIR",
  "reload_file": "$OUT_DIR/evict_reload.md",
  "kept_verbatim": [1, 3],
  "kept_summary": [4],
  "evicted": [2]
}
```

`work_dir` and `reload_file` MUST use the dumper's `$OUT_DIR` from Step 1, so the marker points at
the same tree the turn files actually live in.

**Then verify before you tell the user to clear:** confirm `$OUT_DIR/evict_reload.md` exists and is
non-empty (e.g. `test -s "$OUT_DIR/evict_reload.md" && wc -c < "$OUT_DIR/evict_reload.md"`). If it is
missing or empty, the reload would silently restore nothing — do **not** proceed to Step 6; re-do
Step 4 (and re-run Step 1 if the turn files are gone).

(Do not stamp a timestamp — `date` is unavailable in some sandboxes and it isn't needed.)

## Step 6 — Tell the user to clear

Output exactly this shape (adjust numbers), and nothing more:

```
Staged: keep 1,3 verbatim · summarize 4 · evict 2.

Ready — run /clear to reload only the kept context.
```

If the `SessionStart` hook is **not** registered, append:
`"(Reload hook not installed — after /clear, reopen evict_reload.md manually.)"`

## After /clear (you don't run this)

The `SessionStart` hook (`scripts/reload.sh`) reads `/tmp/.evict_pending.json`, injects
`evict_reload.md` via `hookSpecificOutput.additionalContext` (the SessionStart output channel that
actually enters the model's context — **not** `systemMessage`, which is display-only), deletes the
working dir and pending marker, and the user starts fresh with only their kept context.

The host caps `additionalContext` at 10,000 characters: above that it persists the full text to its
own file and hands the model only a short preview, so a large kept-context would silently fail to
restore. The hook guards against this — payloads under ~9KB inline as above; larger ones are
preserved at a stable path with a short pointer instructing the model to read that file in full
before doing anything else, so the entire kept context is restored regardless of size. (Note: the
context-usage indicator reads 0% until the first message after `/clear` — it measures the last API
turn, and none has happened yet; it shows the true value once you send anything.)

## Edge case — re-invoked before /clear

If `/tmp/.evict_pending.json` already exists with `"pending": true`, a prior evict is staged but not
yet cleared. Re-run from Step 1 (the session has grown), present a fresh block list, and overwrite
the reload file + pending marker. The previous staging is fully superseded — no warning needed.
