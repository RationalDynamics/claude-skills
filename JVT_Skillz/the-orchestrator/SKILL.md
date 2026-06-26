---
name: the-orchestrator
description: >
  Decomposes a design document into a parallelizable directed acyclic graph (DAG) of implementation
  tasks, manages worktree-based parallel execution, and tracks progress via an interactive visual
  workflow. Use this skill whenever the user wants to orchestrate a large implementation from a design
  doc, parallelize work across worktrees, break a design into independent workstreams, or explicitly
  invokes /the-orchestrator. Also trigger when the user says things like "orchestrate this design",
  "parallelize this implementation", "break this into parallel tasks", "create a workflow from this
  design doc", or "set up worktrees for this project". This skill is repository-agnostic — it works
  with any codebase and any design document format.
---

# The Orchestrator

You are decomposing a design document into a parallelizable execution plan, represented as a directed
acyclic graph (DAG). Each node is an independently implementable unit of work. Nodes at the same
level can run in parallel on separate git worktrees. The design document serves as a **mutable
contract** — it is the single source of truth, updated only at level boundaries through a controlled
addendum process.

## Invocation

The user invokes this skill by passing a design document path:

```
/the-orchestrator <path-to-design-doc>
```

If no path is provided, ask for one. The design document can be any format (markdown, text, etc.)
but structured documents with clear work breakdowns produce the best results.

## Step 1: Analyze the Design Document

Read the design document thoroughly. Identify:

1. **Discrete work units** — sections, features, components, or tasks that can be implemented independently
2. **Dependencies** — which units require others to complete first (shared interfaces, data models, APIs that consumers depend on)
3. **Chokepoints** — units that MUST complete before any downstream work can begin (these form level boundaries)
4. **Constraint surface** — what each unit touches (files, modules, APIs) to ensure parallel nodes don't have overlapping file sets

### Partitioning Strategy (in priority order)

1. **Structured breakdown (preferred):** If the design doc has an explicit work breakdown section, section headers, or numbered implementation steps — use those as the primary node boundaries
2. **Explicit markers:** If sections are clearly marked as independent features/components — parse those as nodes
3. **Analytical partitioning:** If the structure is ambiguous, propose a partitioning and present it to the user for approval before proceeding

When partitioning, enforce this rule: **parallel nodes at the same level must not have overlapping file sets.** This guarantees clean merges for the first node at each level and minimizes conflict surface for subsequent rebases. If two work units touch the same files, they must be sequential (different levels) or merged into one node.

## Step 2: Build the DAG

Construct the graph with these properties:

- **Nodes:** Each node represents an independently implementable task
- **Edges:** Directed edges represent dependencies (A → B means A must complete before B can start)
- **Levels:** Nodes with no unmet dependencies form a level. All nodes at a level can execute in parallel
- **Node metadata:**
  - `id`: Unique identifier (e.g., `node-1-auth-service`)
  - `name`: Human-readable name
  - `description`: What this node implements (scoped excerpt from the design doc)
  - `level`: Which level this node belongs to
  - `files`: Expected file paths this node will touch (for overlap detection)
  - `dependencies`: List of node IDs this depends on
  - `mode`: `"solo"` or `"agent-team"` (see recommendation criteria below)
  - `status`: `"red"` | `"blue"` | `"green"` (initialized to `"red"`)

### Agent-Team Recommendations

For each node, recommend solo or agent-team mode:

- **Solo agent:** The node is scoped to a single area or concern (e.g., one service, one component, one module)
- **Agent-team:** The node spans multiple distinct areas that benefit from specialist sub-agents (e.g., backend API + frontend component + integration tests for one feature). When recommending agent-team, specify the recommended team composition (delegator + which specialists)

The recommendation is advisory — the user decides when launching each node.

### Present the DAG for Approval

Before writing anything to disk, present the DAG to the user:

1. Show the level structure (which nodes at each level)
2. Show dependencies between nodes
3. Show the agent-team recommendations with reasoning
4. Show the file overlap analysis (confirm no overlaps within levels)
5. Highlight chokepoints and explain why they can't be parallelized

Wait for user approval or adjustments before proceeding.

## Step 2.5: Verification Setup (Optional)

After the DAG is approved, ask the user:
"Do you want to set up a verification step? This creates a project-specific E2E check
that runs before each level unlock — spinning up the app, navigating pages, and confirming
features work in practice."

If yes:
- Deep-dive the codebase to understand: docker/docker-compose setup, dev server commands,
  test framework, frontend routes, key user flows
- Create `verify/` directory in the orchestrator workspace
- Write `verify/instructions.md` with initial verification steps based on what exists
- Set `verify_enabled: true` in state.json

If no:
- Skip. User can enable later via the sidebar toggle in the viewer.

## Step 3: Initialize `.orchestrator/`

After approval, create the orchestrator workspace:

```
.orchestrator/
└── <design-doc-slug>/
    ├── contract.md              # Living copy of the design document
    ├── graph.json               # DAG definition (nodes, edges, levels, metadata)
    ├── state.json               # Per-node status tracking
    ├── addendums/               # Proposed contract changes during current level (empty initially)
    ├── active/                  # Heartbeat files for active sessions
    ├── verify/                  # Verification playbook and results (optional)
    └── nodes/                   # Per-node context files (populated per-level, not upfront)
```

### `graph.json` Schema

```json
{
  "slug": "<design-doc-slug>",
  "source": "<original-design-doc-path>",
  "repo_root": "<absolute-path-to-git-repo-root>",
  "created": "<ISO-8601 timestamp>",
  "levels": [
    {
      "level": 0,
      "nodes": [
        {
          "id": "node-0-schema",
          "name": "Database Schema",
          "description": "Create the core database tables...",
          "files": ["migrations/001_schema.sql", "db/models.py"],
          "dependencies": [],
          "mode": "solo"
        }
      ]
    }
  ]
}
```

### `state.json` Schema

```json
{
  "current_level": 0,
  "nodes": {
    "node-0-schema": {
      "status": "red",
      "worktree_path": null,
      "started_at": null,
      "completed_at": null
    }
  }
}
```

### `contract.md`

A verbatim copy of the input design document. This is the mutable contract — it gets updated at level boundaries when addendums are consolidated.

## Step 4: Generate Level 0 Node Contexts

Generate context files **only for the current level** (level 0 initially). Each node context file lives at `.orchestrator/<slug>/nodes/<node-id>.md` and contains:

1. **Plan gate** (MUST be the very first line of the file):
   ```
   STOP. Do NOT begin implementing. First, invoke /grill-me — read the skill and ask the
   user clarifying questions about any ambiguities in design, scope, or implementation
   approach. Only after ambiguities are resolved, present a plan for the user to review
   and approve before writing any code.

   During /grill-me, if you discover changes needed outside this node's declared file scope:
   - Implement directly if: one-line fix, zero blast radius on other nodes, or test-blocking
     for this node. Document in your addendum under "## Implemented Changes".
   - Defer if: multi-file change, touches another node's declared scope, or unclear downstream
     impact. Document in your addendum under "## Deferred Changes".
   Always surface both categories to the user with a recommendation before acting.
   ```
2. **Scope:** The specific section of the design doc this node implements (pulled from `contract.md`)
3. **Constraints:** Files this node may touch, interfaces it must respect, boundaries it must not cross
4. **Dependencies:** What prior work this node builds on (none for level 0)
5. **Git context:**
   ```
   You are working in a git worktree at <worktree-path> on branch orchestrator/<slug>/<node-id>.
   The main repo is at <repo_root> (from graph.json).
   Git requires worktrees to be on separate branches — this is expected, not an error.

   During development: commit your work to THIS branch (the worktree branch).
   During merge: you will merge this branch into the feature branch from the main repo.
   To determine the feature branch, run: git -C <repo_root> branch --show-current
   ```
6. **Workflow instructions:**
   ```
   IMPORTANT: The .orchestrator/ directory lives in the MAIN repo, NOT in your worktree.
   All state.json updates and addendum writes must target the main repo path:
   <repo_root>/.orchestrator/<slug>/

   If `<repo_root>/.orchestrator/<slug>/addendums/patches.md` exists, read it at session
   start to understand direct fixes applied to the feature branch since your worktree
   was created.

   After all tests pass, update <repo_root>/.orchestrator/<slug>/state.json to set this node's status to "blue".
   Then proceed to the merge workflow:
   1. cd to the main repo: cd <repo_root>
   2. Get the feature branch: git branch --show-current
   3. If this is the first completed node at this level: git merge orchestrator/<slug>/<node-id> --no-ff
      Otherwise: rebase first from the worktree, then merge:
      git -C <worktree-path> rebase <feature-branch>
      git merge orchestrator/<slug>/<node-id> --no-ff
   4. Re-run all tests
   5. If tests pass: update state.json status to "green", then clean up:
      git worktree remove <worktree-path> && git branch -d orchestrator/<slug>/<node-id>
   6. If merge conflicts arise: keep status as "blue" and surface conflicts for manual resolution

   CRITICAL: Stay in the main repo (cd <repo_root>) for the entire merge + cleanup sequence.
   Do NOT cd back to the worktree — it will be removed during cleanup and your shell will
   be stuck in a dead directory that breaks all subsequent commands.

   DO NOT include a "Co-Authored-By" signature in any commit messages.

   If the design requires changes beyond this node's scope, write an addendum to:
   <repo_root>/.orchestrator/<slug>/addendums/<node-id>-<description>.md
   describing the proposed change and its rationale.

   If merge conflicts occur OR tests fail after merging:
   1. Read sibling node addendums at the current level:
      ls <repo_root>/.orchestrator/<slug>/addendums/
      Look at "Implemented Changes" sections — these out-of-scope changes
      by parallel nodes may explain the conflict or failure.
   2. Apply the same blast-radius logic to fixes:
      - Small fix, zero blast radius → implement + document under "Implemented Changes"
      - Large blast radius → defer + document under "Deferred Changes"
      - Always surface to the user for approval
   3. Document in this node's addendum: what failed, what was fixed,
      what was deferred, and the drift-impact assessment.

   Do NOT read sibling addendums preemptively before merge — only on failure.

   If a verifier is enabled (.orchestrator/<slug>/verify/instructions.md exists), verification
   runs at the level boundary after all nodes are green — you do not need to run it yourself.
   Focus on unit/integration tests within your node scope.
   ```
6. **Agent-team guidance** (if mode is `"agent-team"`): The recommended team composition and delegation strategy. The delegator agent should ALWAYS be told to delegate and orchestrate only, not implement anything itself. Sub-agents employ peer-to-peer messaging.

## Step 5: Launch the Viewer

After initializing the workspace, launch the interactive DAG viewer:

```bash
python3 ~/.claude/skills/the-orchestrator/scripts/server.py \
  .orchestrator/<slug>/ &
```

This starts a local HTTP server that:
- Serves the interactive DAG visualization
- Exposes `GET /api/state` for the viewer to poll node statuses
- Exposes `POST /api/state/<node-id>` for programmatic status updates
- Exposes `POST /api/unlock-next-level` to trigger level transitions

Tell the user: "The orchestrator viewer is running at http://localhost:5000. Click any red node at level 0 to launch a terminal with the node's context loaded."

## Level Transition Protocol

When all nodes at the current level are green and the user clicks "Unlock Next Level" in the viewer:

1. **Two parallel `claude -p --model opus` invocations are triggered:**

   **Contract Updater** (only if `addendums/` is non-empty):
   - Reads all files in `addendums/`
   - Reads current `contract.md`
   - Consolidates addendums into the contract, maintaining document coherence
   - Writes updated `contract.md`
   - Purges all files from `addendums/`

   **Context Generator** (runs after contract updater completes, or immediately if no addendums):
   - Reads updated `contract.md` and `graph.json`
   - Purges previous level's node context files from `nodes/`
   - Generates fresh `nodes/<node-id>.md` for each node in the next level
   - Each context file follows the same structure as Step 4, incorporating any contract changes

2. **After both complete:** The viewer unlocks the next level's nodes (they become clickable)

## Node Click Behavior

When a node is clicked in the viewer, the behavior depends on its status:

### Red Node (not started)
Opens a new Terminal window via `osascript` that:
1. `cd`s to the worktree directory for this node (created if it doesn't exist)
2. Launches `claude` with the node's context file pre-loaded
3. Updates `state.json` to record `worktree_path` and `started_at`

The terminal launch command:
```bash
# Create worktree if needed
git worktree add .worktrees/<node-id> -b orchestrator/<slug>/<node-id>

# Launch claude with context
cd .worktrees/<node-id>
claude --resume-from ~/.orchestrator-sessions/<slug>/<node-id> \
  -p "$(cat .orchestrator/<slug>/nodes/<node-id>.md)"
```

### Blue Node (done, not merged)
The implementation session handles the merge workflow internally — blue is a transient state.
If a node is stuck on blue (merge conflict), clicking it re-opens the terminal in the worktree
so the user can resolve conflicts with full session context.

### Green Node (merged)
No action — displays completion details (timestamp, duration) on hover.

## Addendum Protocol

During any implementation session, if the design requires changes beyond the current node's scope:

1. The session writes a markdown file to `.orchestrator/<slug>/addendums/<node-id>-<short-description>.md`
2. The addendum contains:
   - **Proposed change:** What needs to change in the design doc
   - **Rationale:** Why this change is needed (discovered during implementation)
   - **Impact:** Which downstream nodes might be affected
   - **Implemented Changes** (optional): Out-of-scope changes this node implemented directly
   - **Deferred Changes** (optional): Out-of-scope changes identified but left for other nodes
3. Addendums are consolidated into the contract at the next level transition
4. The contract can ONLY change at level boundaries — never mid-level

### Addendum Structure

Addendums may include two optional sections for tracking out-of-scope changes:

```markdown
## Implemented Changes
- **File**: `path/to/file` | **Change**: description | **Reason**: why implemented here

## Deferred Changes
- **Description**: what needs to change | **Affects**: which downstream nodes | **Reason**: why deferred
```

These sections are optional — addendums without them remain valid. They help sibling nodes
understand what out-of-scope work was done or identified during parallel implementation.

## Feature Queue

Users can spec out new requirements mid-orchestration by adding feature requests to a queue. The queue is stored as specially-named files in the `addendums/` directory.

### File Naming Convention

Feature queue files use the `user_request_` prefix:

```
.orchestrator/<slug>/addendums/user_request_<short-kebab-description>.md
```

### File Format

```markdown
# User Request: <Title>

## Summary
<1-2 sentence summary of the feature/request>

## Specification
<Detailed specification of what needs to be implemented>

## Priority
<high | medium | low — with brief justification>

## Affected Areas
<Which parts of the codebase / which existing or future nodes this affects>
```

### Integration with Level Transitions

- When "Unlock Next Level" is triggered, `user_request_*.md` files in `addendums/` are included in the addendum consolidation step alongside regular node addendums. The restructuring step (which evaluates the graph) naturally sees the expanded contract and can adjust the graph accordingly.
- After a successful level transition, all `user_request_*.md` files are deleted from `addendums/` to clear the queue.

### Integration with Update Graph

- The "Update Graph" action triggers a mid-level graph restructuring that reads all queued `user_request_*.md` files and restructures the DAG to accommodate them.
- Unlike level-transition restructuring (which only allows new nodes at the next level or higher), Update Graph allows new nodes at the **current level** or higher, enabling immediate work on queued features.
- After a successful graph update, all `user_request_*.md` files are deleted from `addendums/`.
- Update Graph is blocked when: the queue is empty, all current-level nodes are already green (use Unlock Next Level instead), or a transition is already running.

## Worktree Management

- Each parallel node gets its own worktree branched from the current feature branch
- Worktree location: `.worktrees/<node-id>/` (relative to repo root)
- Branch naming: `orchestrator/<slug>/<node-id>`
- After a node goes green (merged), its worktree and branch can be cleaned up
- The orchestrator tracks worktree paths in `state.json`

## Merge Protocol (per level)

Nodes at a level complete asynchronously. The merge order matters:

1. **First node to complete at a level:** Direct merge to the feature branch (no rebase needed)
2. **Each subsequent node:** Rebase onto the (now-updated) feature branch → resolve any conflicts → merge → re-run tests
3. **If conflicts arise:** Node stays blue, conflicts surfaced to user in the active terminal session (which has full implementation context)
4. **After successful merge:** Node status → green, `state.json` updated, worktree cleaned up

This is handled within each node's implementation session — the instructions are embedded in the node context files.

## Completion

The orchestration is complete when all nodes across all levels are green. The viewer shows the fully green DAG as the final state. The `.orchestrator/<slug>/` directory persists as a record of the orchestration.

## Important Constraints

- **No upfront context generation.** Node contexts are generated only for the current active level, fresh each time, incorporating any contract changes from addendums.
- **No overlapping file sets within a level.** This is enforced during DAG construction to minimize merge conflicts.
- **Contract changes only at level boundaries.** Mid-level changes are captured as addendums and consolidated before the next level begins.
- **The design doc is the source of truth.** `contract.md` is always the authoritative version — the original file is not modified.
- **Parallel nodes use independent worktrees.** Never two nodes working in the same worktree.
