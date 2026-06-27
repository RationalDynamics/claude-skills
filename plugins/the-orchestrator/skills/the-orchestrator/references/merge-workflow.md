# Merge Workflow Reference

This document describes the merge protocol used by orchestrator nodes after implementation
and testing are complete. It is embedded into each node's context file automatically.

## Prerequisites

Before starting the merge workflow:
- All tests pass in the node's worktree
- `state.json` has been updated to `"blue"` for this node

CRITICAL: `cd` to the MAIN repo and stay there for the entire merge + cleanup sequence.
Do NOT `cd` back to the worktree at any point — it will be removed during cleanup and
your shell will be stuck in a dead directory that breaks all subsequent commands.

DO NOT include a "Co-Authored-By" signature in any commit messages.

## Determine Merge Order

Check `.orchestrator/<slug>/state.json` to see if any other nodes at this level have already
merged (status = `"green"`).

### First Node at Level (no other green nodes at this level)

```bash
# Switch to the feature branch
git checkout <feature-branch>

# Merge the worktree branch
git merge orchestrator/<slug>/<node-id> --no-ff -m "Merge <node-id>: <node-name>"

# Run tests
<project-specific-test-command>

# If tests pass, clean up
git worktree remove .worktrees/<node-id>
git branch -d orchestrator/<slug>/<node-id>
```

### Subsequent Nodes at Level (other green nodes exist)

```bash
# In the worktree, rebase onto updated feature branch
git rebase <feature-branch>

# If conflicts arise:
#   1. Resolve conflicts
#   2. git rebase --continue
#   3. If conflicts are non-trivial, STOP and surface to user
#      Keep status as "blue" — do NOT force through unclear conflicts

# After clean rebase, switch to feature branch
git checkout <feature-branch>

# Merge
git merge orchestrator/<slug>/<node-id> --no-ff -m "Merge <node-id>: <node-name>"

# Re-run ALL tests (not just this node's tests — the rebase may have introduced issues)
<project-specific-test-command>

# If tests pass, clean up
git worktree remove .worktrees/<node-id>
git branch -d orchestrator/<slug>/<node-id>
```

## Status Updates

After each phase, update `.orchestrator/<slug>/state.json`:

| Phase | Status | When |
|-------|--------|------|
| Implementation + tests pass | `"blue"` | All tests pass in worktree |
| Merge succeeds + tests pass | `"green"` | Post-merge tests pass on feature branch |
| Merge conflict | Stay `"blue"` | Conflicts surfaced to user |
| Post-merge test failure | Stay `"blue"` | Investigate failure in current terminal |

## Conflict Resolution

When conflicts arise during rebase:

1. **Do NOT auto-resolve ambiguous conflicts.** Surface them to the user with full context.
2. Show which files conflict and why (the other node's changes vs this node's changes).
3. The user resolves in the current terminal — this is why blue nodes keep the session alive.
4. After resolution, continue the rebase and re-run tests.

## Worktree Cleanup

After a successful merge (status → green):

```bash
# Remove the worktree
git worktree remove .worktrees/<node-id>

# Delete the branch
git branch -d orchestrator/<slug>/<node-id>
```

If the worktree removal fails (e.g., uncommitted changes), warn the user rather than force-removing.

## Writing Addendums

If during implementation you discover that the design needs changes beyond this node's scope:

1. Write a markdown file to `.orchestrator/<slug>/addendums/<node-id>-<short-description>.md`
2. Structure:
   ```markdown
   # Addendum: <short description>

   ## Proposed Change
   <What needs to change in the design doc>

   ## Rationale
   <Why this was discovered during implementation>

   ## Impact
   <Which downstream nodes or features might be affected>

   ## Implemented Changes
   - **File**: `path/to/file` | **Change**: description | **Reason**: why implemented here

   ## Deferred Changes
   - **Description**: what needs to change | **Affects**: which downstream nodes | **Reason**: why deferred
   ```
3. The "Implemented Changes" and "Deferred Changes" sections are optional — include them only
   when out-of-scope changes were implemented or identified during this node's work.
4. This will be consolidated into the contract at the next level transition.
5. Do NOT modify `contract.md` directly — addendums are the only mechanism for mid-level changes.

## Post-Merge Failure: Sibling Addendum Context

When merge conflicts occur or tests fail after merging, sibling node addendums can provide
critical context about out-of-scope changes that may explain the failure.

### When to Check

Only check sibling addendums when:
- A merge conflict occurs during rebase or merge
- Tests fail after a successful merge

Do NOT read sibling addendums preemptively before merge — only on failure.

### How to Find Them

```bash
# List all addendums at the current level
ls <repo_root>/.orchestrator/<slug>/addendums/

# Read sibling node addendums (files not prefixed with your own node-id)
cat <repo_root>/.orchestrator/<slug>/addendums/<sibling-node-id>-*.md
```

### What to Look For

Focus on the "Implemented Changes" sections in sibling addendums. These document out-of-scope
changes that parallel nodes made directly — changes that may have modified files or interfaces
your node also depends on.

### Blast-Radius Decision Logic for Fixes

When you identify the cause of a conflict or test failure from sibling addendum context:

- **Small fix, zero blast radius** → implement the fix directly and document it under
  "Implemented Changes" in your own addendum
- **Large blast radius** (multi-file change, touches another node's scope, unclear downstream
  impact) → defer the fix and document it under "Deferred Changes" in your own addendum
- **Always surface to the user for approval** before acting on either path

### Documentation

After resolving (or deferring) a post-merge issue, document in your own addendum:
- What failed (conflict details or test failure output)
- What was fixed and how
- What was deferred and why
- Drift-impact assessment: how the sibling's out-of-scope change affects downstream nodes
