---
name: breakpoint
description: >
  Insert context checkpoint markers into the conversation. Use /breakpoint to mark transitions
  between logical work segments — starting a tangent, switching tasks, or returning to a main
  workflow. These markers enable /neuralize to later selectively evict irrelevant context segments
  and reclaim context window space.
disable-model-invocation: true
---

# Breakpoint

You are a context checkpointing tool. Your job is simple: insert a marker that divides the conversation into logical blocks, and persist the block content to disk so it can be selectively reloaded later via `/neuralize`.

## How it works

Each breakpoint divides the conversation into **blocks**. The first block starts at the beginning of the session. Each subsequent block starts where the previous one ended.

When invoked, you do three things:

1. **Determine open/close state** by scanning the conversation for unmatched `<BREAKPOINT>` tags
2. **Write the completed block** (the content between the last marker and now) to disk
3. **Output the marker** into the conversation

## Step-by-step

### 1. Read config

Read `~/.claude/skills/breakpoint/config.yaml` to determine the storage mode:
- `persist: false` (default) → store in `/tmp/claude-breakpoints/`
- `persist: true` → store in `~/.claude/breakpoints/`

### 2. Determine or create the session directory

Check if a breakpoint session directory already exists for this conversation by looking for a `.breakpoint_session` file in the working directory or `/tmp/claude-breakpoints/`. If this is the first breakpoint in the session, create the session directory:

```
<storage-root>/<git-branch>[_<worktree-name>]_<timestamp>_<5-char-random>/
```

- `<git-branch>`: current git branch name (use `git branch --show-current`, fall back to `"no-branch"`)
- `<worktree-name>`: only include if inside a git worktree (detect via `git rev-parse --show-toplevel` differing from `git rev-parse --git-common-dir`'s parent). Use the worktree directory basename.
- `<timestamp>`: `YYYY-MM-DDTHH-MM-SS`
- `<5-char-random>`: 5 lowercase alphanumeric characters

Write the full session directory path to `/tmp/.breakpoint_active_session` so both the breakpoint and neuralize skills can find it across invocations.

### 3. Scan for open/close state

Scan the conversation for `<BREAKPOINT>` and `</BREAKPOINT>` tags:
- If no unmatched `<BREAKPOINT>` exists → this invocation **opens** a new breakpoint
- If an unmatched `<BREAKPOINT>` exists → this invocation **closes** it

### 4. Write the block to disk

Capture the raw conversation content from the end of the previous marker (or session start) up to this invocation. Write it to:

```
<session-dir>/block-<N>.md
```

Where N is the sequential block number starting at 1.

Use this format:

```markdown
---
block: <N>
label: "<user-provided label or auto-generated one-line description>"
type: <open|close>
timestamp: <ISO 8601>
---

<raw conversation content for this block>
```

The label is either:
- Provided by the user: `/breakpoint "debugging CI pipeline"` → `"debugging CI pipeline"`
- Auto-generated: a single sentence summarizing what was discussed/accomplished in this block

### 5. Output the marker

**If opening:**
```
<BREAKPOINT>
--- Checkpoint: Block <N> saved | "<label>" ---
```

**If closing:**
```
</BREAKPOINT>
--- Checkpoint: Block <N> saved | "<label>" ---
```

Keep the output minimal. Do not add commentary, summaries, or suggestions. The marker and confirmation line are the entire output.

## Handling the `--persist` flag

If the user invokes `/breakpoint --persist`, override the config for this session only:
- If blocks were previously written to `/tmp/`, move the entire session directory to `~/.claude/breakpoints/`
- Update `/tmp/.breakpoint_active_session` to point to the new location
- All subsequent blocks in this session go to the persistent location

## Edge cases

- **First invocation is always an open.** There's no prior block to close.
- **Back-to-back opens without a close**: Treat each open as closing the previous block and opening a new one. Every invocation writes a block.
- **No git repo**: Use `"no-branch"` as the branch component.
