# The Orchestrator

Decomposing a design document into a parallelizable directed acyclic graph (DAG) of implementation tasks, managing worktree-based parallel execution, and tracking progress via an interactive visual workflow.

## What

*/the-orchestrator* is a  skill that decomposes a design document into a parallelizable directed acyclic graph (DAG) of implementation tasks. Each node in the graph is an independently implementable unit of work that runs in its own git worktree. Nodes at the same level execute in parallel. Progress is tracked via an interactive browser-based DAG viewer where you click nodes to launch terminal sessions and watch them go from red (pending) to blue (done) to green (merged).

Currently designed for Claude Code and mono-repo structures, with potential support for Codex and other tools and non-mono-repo setups in the future.

## Why

Large implementations from a single design doc are sequential by default — you work through one piece, then the next, then the next. This is slow and doesn't leverage the fact that many pieces are independent. The Orchestrator identifies which pieces can run in parallel, isolates them in worktrees so they don't conflict, manages the merge protocol between them, and keeps the design document as a living contract that evolves with what you learn during implementation. It turns a linear slog into a parallelized workflow with visual progress tracking.

## Quick Start

### 1. Start with an idea

You don't need a polished design document to begin. Start with whatever you have — a rough sketch, a bullet list, a half-formed idea. Open a Claude Code session and iterate:

```
I want to build a real-time notification system with in-app notifications,
email digests, and webhook delivery. Users should be able to configure
preferences per channel. Help me flesh this out into a design doc.
```

Work with Claude to resolve open questions: What's the data model? What are the API endpoints? What's the state machine? What are the dependencies between components? The goal is a document that's specific enough to break into parallel work units.

### 2. Produce a design document

Save your design as a markdown file. The more structured it is, the better the orchestrator can partition it. A good design doc includes:

- **Work breakdown** — distinct features, components, or layers with clear boundaries
- **Dependencies** — which pieces require others to complete first
- **File scope** — which files each piece will touch (helps ensure parallel nodes don't collide)

The document doesn't need to be perfect — the orchestrator's addendum system lets it evolve as you learn during implementation.

### 3. Run the orchestrator

```
/the-orchestrator path/to/your-design.md
```

The orchestrator will analyze your design, build a DAG, and present it for your approval. After you approve, it creates the `.orchestrator/` workspace and launches the viewer.

### 4. Work through the graph

Open the viewer at `localhost:5000`. Click red nodes to launch terminal sessions. Each session:
- Asks clarifying questions (`/grill-me`) before planning
- Presents a plan for your approval
- Implements with TDD after approval
- Merges back to the feature branch when done

When all nodes at a level are green, unlock the next level and repeat.

## Installation

Copy or symlink the `the-orchestrator/` directory into `~/.claude/skills/`.

## Setup

### 1. Required skills

The orchestrator's node context instructions invoke these skills. Install them before using the orchestrator:

- `/grill-me` — interrogates ambiguities in design or implementation before proceeding
- `/tdd` — test-driven development workflow (write failing tests first, then implement)

Without these skills installed, node sessions will reference commands that don't exist.

### Recommended: `/esoteric-elucidation`

If during a node session the model is dumping walls of technical code and jargon at you without orienting you first, invoke `/esoteric-elucidation`. It restructures how the model explains code and systems — plain-English context first, implementation details second. Especially useful when reviewing plans for parts of the codebase you're less familiar with.

### 2. Post-plan-approval hook (STRONGLY recommended)

The orchestrator launches node sessions in plan mode. After you approve a plan, this hook reminds the model to consider TDD before writing code. It only fires in orchestrator sessions (gated by the `ORCHESTRATOR_SESSION` env var).

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/skills/the-orchestrator/scripts/on-plan-approved.sh"
          }
        ]
      }
    ]
  }
}
```

If you already have a `hooks` key in your settings, merge the `PostToolUse` entry into it.

### 3. Dependencies

- **Claude Code CLI** (`claude`) — must be on your PATH
- **Git** — worktree support required (Git 2.5+)
- **Python 3** — for the viewer server and transition scripts
- **D3.js + dagre** — loaded from CDN in the viewer (requires internet on first load)

## Usage

```
/the-orchestrator <path-to-design-doc>
```

Or naturally: "Orchestrate this design doc: path/to/design.md"

The orchestrator will:

1. Analyze the design document and build a DAG
2. Present the graph for your approval (levels, nodes, dependencies, agent-team recommendations)
3. Optionally set up a verification playbook (E2E acceptance checks)
4. Create `.orchestrator/<slug>/` with the contract, graph, state, and level-0 node contexts
5. Launch the viewer server at `localhost:5000`

### Working through the DAG

- **Click a red node** at the current level to launch a terminal in a new worktree with context pre-loaded
- Each session runs in **plan mode** — the model invokes `/grill-me` first, then presents a plan for approval
- After plan approval, the post-plan hook reminds the model to consider `/tdd`
- After implementation + tests pass, the session handles the merge workflow automatically
- Node colors: **red** (not started) | **blue** (done, merging) | **green** (merged) | **gold border** (active session)
- Active nodes are locked (non-clickable) while their terminal session is open (heartbeat-based detection)
- When all nodes at a level are green, run verification (if enabled) then click **Unlock Next Level** to advance

### Level transitions

Unlocking the next level triggers:

1. Addendum consolidation into the design contract (if any addendums were written)
2. Graph restructuring evaluation (adds/removes/modifies unstarted nodes if the contract changed significantly)
3. Fresh node context generation for the next level's nodes
4. A progress banner in the viewer showing each phase

### Addendums

If during implementation a session discovers the design needs changes beyond its scope, it writes an addendum to `.orchestrator/<slug>/addendums/`. Addendums may include:

- **Implemented Changes** — small out-of-scope fixes made directly (documented for sibling node awareness)
- **Deferred Changes** — larger changes left for future nodes

On merge conflict or post-merge test failure, nodes check sibling addendums for context.

### Feature queue

Use the collapsible left sidebar to manage mid-project changes:

- **+ Add Feature** — launches a terminal session to spec out a new requirement with `/grill-me`. The spec is saved as a queued addendum.
- **Active queue** — lists pending feature requests below the button
- **Update Graph** — restructures the DAG to incorporate queued features (only available when nodes are in progress, not when all are green)
- Queued features are also ingested when unlocking the next level

### Patch

For quick fixes that don't belong to any node:

- **Patch** button in the sidebar — launches a terminal on the feature branch (no worktree) to make a direct fix
- Only available when no node sessions are active (serialized to prevent sync issues)
- Fixes are logged in `addendums/patches.md` for future nodes to reference

### Verifier (optional)

E2E acceptance checks that gate level unlocks — catches "tests pass but the app is broken" scenarios.

- **Setup** — during first orchestrator invocation, you're asked if you want a verifier. If yes, the orchestrator deep-dives the codebase and writes an initial playbook (`verify/instructions.md`)
- **Toggle** — gold switch in the sidebar. When on, shows a playbook editor where you can view/edit the verification steps. When off, verification is skipped entirely
- **Verify Level** — blue button in the header bar, appears when the verifier toggle is on. Only clickable when all nodes at the current level are green. Runs a two-step process:
  1. Programmatic playbook update — adapts `instructions.md` based on what was just built (addendums + patches)
  2. Interactive evaluator terminal — a fresh-context agent with a skeptical prompt executes the playbook step by step, reports pass/fail
- **Pass** — button turns green, "Unlock Next Level" enables
- **Fail** — failures listed in terminal + `last_result.json`. Use Patch to fix, then re-verify
- **Staleness** — applying a patch after verification passes invalidates the result. Must re-verify before unlocking
- **Backwards compatible** — no `verify/` folder means no verifier, everything works as before

## File structure

```
the-orchestrator/
  SKILL.md                          # Main skill instructions (loaded by Claude)
  README.md                         # This file (not loaded by Claude)
  assets/
    viewer.html                     # Interactive DAG viewer (D3.js + dagre)
    orchestrator_logo.svg           # Logo displayed in the viewer header
  references/
    merge-workflow.md               # Merge protocol reference
  scripts/
    server.py                       # Viewer server + API + node launcher
    transition.py                   # Standalone level transition script
    on-plan-approved.sh             # Post-plan-approval hook for TDD reminder
```

## Project workspace

When invoked, the orchestrator creates:

```
.orchestrator/<slug>/
  contract.md           # Living copy of the design document
  graph.json            # DAG definition (nodes, edges, levels, repo_root)
  state.json            # Per-node status + transition state/phase
  addendums/            # Proposed contract changes (purged at level transitions)
    patches.md          # Cumulative log of direct patches (append-only)
    user_request_*.md   # Queued feature specs (cleared after graph update)
  active/               # Heartbeat files for session lock detection
  nodes/                # Per-node context files (regenerated per level)
  verify/               # Verification playbook and results (optional)
    instructions.md     # E2E acceptance playbook (edited via sidebar)
    last_result.json    # Latest verification result (pass/fail + failures)
```

Worktrees are created at `.worktrees/<node-id>/` relative to the repo root.

## API endpoints

The viewer server exposes these endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Viewer HTML |
| GET | `/api/state` | Node statuses + lock state + transition status |
| GET | `/api/graph` | DAG structure |
| GET | `/api/queue` | Pending feature requests |
| POST | `/api/launch/<id>` | Launch node terminal in worktree |
| POST | `/api/heartbeat/<id>` | Session heartbeat (called by terminal loop) |
| POST | `/api/state/<id>` | Update node status |
| POST | `/api/unlock-next-level` | Trigger level transition |
| POST | `/api/add-feature` | Launch feature spec terminal |
| POST | `/api/update-graph` | Restructure DAG for queued features |
| POST | `/api/patch` | Launch patch terminal on feature branch |
| GET | `/api/verify-status` | Verifier state (enabled, status, failures) |
| GET | `/api/verify-instructions` | Current playbook content |
| POST | `/api/verify-instructions` | Save playbook content |
| POST | `/api/verify-level` | Run verification (update playbook + launch evaluator) |
| POST | `/api/verify-toggle` | Toggle verifier on/off |
