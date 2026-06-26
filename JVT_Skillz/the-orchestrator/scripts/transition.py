#!/usr/bin/env python3
"""
Standalone level transition script for The Orchestrator.

Consolidates addendums into the contract and generates node contexts
for the next level. Can be run independently of the viewer server.

Usage:
    python3 transition.py <orchestrator-dir> [--level N]
    python3 transition.py .orchestrator/my-feature/ --level 2
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _parse_and_write_nodes(output: str, nodes_dir: Path):
    """Parse delimited node content from claude output and write files."""
    import re
    pattern = r'===NODE:([^=]+)===\s*\n(.*?)===END_NODE==='
    matches = re.findall(pattern, output, re.DOTALL)
    if not matches:
        print("[transition] Warning: no node delimiters found in output", file=sys.stderr)
        return
    for node_id, content in matches:
        node_id = node_id.strip()
        file_path = nodes_dir / f"{node_id}.md"
        file_path.write_text(content.strip() + "\n")
        print(f"[transition] Wrote {file_path}")


def _find_repo_root(start_path: Path) -> Path:
    """Walk up from start_path to find the git repo root."""
    path = start_path.resolve()
    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent
    return start_path.resolve().parent


def consolidate_addendums(orch_dir: Path) -> bool:
    """Consolidate addendums into the contract. Returns True if changes were made."""
    addendums_dir = orch_dir / "addendums"
    if not addendums_dir.exists():
        return False

    addendum_files = list(addendums_dir.glob("*.md"))
    if not addendum_files:
        return False

    print(f"[transition] Consolidating {len(addendum_files)} addendum(s)...")

    addendum_content = ""
    for f in sorted(addendum_files):
        addendum_content += f"## Addendum: {f.stem}\n\n{f.read_text()}\n\n"

    contract_path = orch_dir / "contract.md"
    contract = contract_path.read_text()

    prompt = f"""You are updating a design document contract based on implementation addendums.

Current contract:
---
{contract}
---

Addendums to incorporate:
---
{addendum_content}
---

Consolidate these addendums into the contract. Maintain document coherence and structure.
Update relevant sections in-place rather than appending. Remove any sections that addendums
explicitly supersede.

Output the complete updated contract between these delimiters:
===UPDATED_CONTRACT===
<complete contract text>
===END_CONTRACT==="""

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"[transition] Contract update failed: {result.stderr}", file=sys.stderr)
            return False

        import re
        match = re.search(r'===UPDATED_CONTRACT===\s*\n(.*?)===END_CONTRACT===',
                          result.stdout, re.DOTALL)
        if match:
            contract_path.write_text(match.group(1).strip())
            print("[transition] Contract updated successfully")
        elif result.stdout.strip():
            print("[transition] Warning: contract update output missing delimiters — skipping", file=sys.stderr)
            return False

        # Purge addendums
        for f in addendum_files:
            f.unlink()
        print(f"[transition] Purged {len(addendum_files)} addendum(s)")
        return True

    except subprocess.TimeoutExpired:
        print("[transition] Contract update timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[transition] 'claude' CLI not found — is it installed?", file=sys.stderr)
        return False


def evaluate_graph_restructuring(orch_dir: Path, level: int) -> bool:
    """Evaluate whether graph.json needs restructuring based on contract changes."""
    import re

    graph = json.loads((orch_dir / "graph.json").read_text())
    contract = (orch_dir / "contract.md").read_text()
    state = json.loads((orch_dir / "state.json").read_text())

    # Build immutable set: nodes with status "green" or "blue"
    immutable_ids = set()
    for node_id, ns in state.get("nodes", {}).items():
        if ns.get("status") in ("green", "blue"):
            immutable_ids.add(node_id)

    immutable_list = ", ".join(sorted(immutable_ids)) if immutable_ids else "(none)"

    prompt = f"""You are evaluating whether a DAG graph needs restructuring after a design contract update.

Current graph.json:
---
{json.dumps(graph, indent=2)}
---

Updated contract:
---
{contract}
---

Immutable node IDs (status green or blue — MUST NOT be modified or removed):
{immutable_list}

Evaluate whether the graph needs restructuring. Consider:
- Should any red (pending) nodes be split into smaller nodes?
- Should any red nodes be merged together?
- Should new nodes be added to cover contract changes?
- Should any red nodes be removed because they're no longer needed?

Rules:
- Immutable nodes (listed above) must remain exactly as they are — same id, same level, same fields
- New nodes may only be placed at level {level} or higher
- No two nodes at the same level may have overlapping files
- The top-level "slug" and "repo_root" fields must be preserved exactly
- All node dependencies must reference existing nodes at strictly lower levels
- Every node must have: id, name, description, files (array), dependencies (array), mode

If restructuring is needed, output:
===RESTRUCTURED_GRAPH===
<the complete updated graph.json>
===END_RESTRUCTURED_GRAPH===

If no restructuring is needed, output exactly:
===NO_RESTRUCTURING_NEEDED==="""

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"[transition] Graph restructuring evaluation failed: {result.stderr}", file=sys.stderr)
            return False

        output = result.stdout.strip()

        if "===NO_RESTRUCTURING_NEEDED===" in output:
            print("[transition] No graph restructuring needed")
            return False

        match = re.search(r'===RESTRUCTURED_GRAPH===\s*\n(.*?)===END_RESTRUCTURED_GRAPH===', output, re.DOTALL)
        if not match:
            print("[transition] Warning: ambiguous restructuring output — skipping", file=sys.stderr)
            return False

        try:
            new_graph = json.loads(match.group(1).strip())
        except json.JSONDecodeError as e:
            print(f"[transition] Warning: invalid JSON in restructured graph — skipping: {e}", file=sys.stderr)
            return False

        # Validate the restructured graph
        validate_restructured_graph(graph, new_graph, immutable_ids)

        # Write the new graph
        (orch_dir / "graph.json").write_text(json.dumps(new_graph, indent=2))
        print("[transition] Graph restructured successfully")

        # Update state.json: add entries for new nodes, remove entries for deleted red nodes
        state = json.loads((orch_dir / "state.json").read_text())

        old_node_ids = set()
        for lvl in graph["levels"]:
            for node in lvl["nodes"]:
                old_node_ids.add(node["id"])

        new_node_ids = set()
        for lvl in new_graph["levels"]:
            for node in lvl["nodes"]:
                new_node_ids.add(node["id"])

        # Add state entries for new nodes
        for node_id in new_node_ids - old_node_ids:
            state["nodes"][node_id] = {"status": "red"}

        # Remove state entries for deleted nodes (only if they were red)
        for node_id in old_node_ids - new_node_ids:
            if state["nodes"].get(node_id, {}).get("status") == "red":
                del state["nodes"][node_id]

        (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
        return True

    except subprocess.TimeoutExpired:
        print("[transition] Graph restructuring evaluation timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[transition] 'claude' CLI not found — is it installed?", file=sys.stderr)
        return False
    except RuntimeError as e:
        print(f"[transition] Graph restructuring validation failed: {e}", file=sys.stderr)
        return False


def validate_restructured_graph(old_graph: dict, new_graph: dict, immutable_ids: set):
    """Validate that a restructured graph preserves immutable nodes and structural rules."""
    # Build lookup for new graph nodes
    new_nodes = {}
    for lvl in new_graph["levels"]:
        for node in lvl["nodes"]:
            new_nodes[node["id"]] = {"node": node, "level": lvl["level"]}

    # Build lookup for old graph nodes
    old_nodes = {}
    for lvl in old_graph["levels"]:
        for node in lvl["nodes"]:
            old_nodes[node["id"]] = {"node": node, "level": lvl["level"]}

    # Every immutable node must exist with same id and level
    for node_id in immutable_ids:
        if node_id not in new_nodes:
            raise RuntimeError(f"Restructured graph removed immutable node: {node_id}")
        if new_nodes[node_id]["level"] != old_nodes[node_id]["level"]:
            raise RuntimeError(
                f"Restructured graph changed level of immutable node {node_id}: "
                f"{old_nodes[node_id]['level']} -> {new_nodes[node_id]['level']}"
            )

    # All dependencies must reference existing nodes at lower levels
    for node_id, info in new_nodes.items():
        for dep in info["node"].get("dependencies", []):
            if dep not in new_nodes:
                raise RuntimeError(
                    f"Node {node_id} depends on non-existent node: {dep}"
                )
            if new_nodes[dep]["level"] >= info["level"]:
                raise RuntimeError(
                    f"Node {node_id} (level {info['level']}) depends on "
                    f"node {dep} (level {new_nodes[dep]['level']}) which is not at a lower level"
                )

    # slug and repo_root must be preserved
    if new_graph.get("slug") != old_graph.get("slug"):
        raise RuntimeError(
            f"Restructured graph changed slug: {old_graph.get('slug')} -> {new_graph.get('slug')}"
        )
    if new_graph.get("repo_root") != old_graph.get("repo_root"):
        raise RuntimeError(
            f"Restructured graph changed repo_root: {old_graph.get('repo_root')} -> {new_graph.get('repo_root')}"
        )


def generate_contexts(orch_dir: Path, level: int):
    """Generate node context files for the given level."""
    graph = json.loads((orch_dir / "graph.json").read_text())
    contract = (orch_dir / "contract.md").read_text()
    repo_root = _find_repo_root(orch_dir)
    nodes_dir = orch_dir / "nodes"

    # Find nodes at target level
    level_nodes = None
    for lvl in graph["levels"]:
        if lvl["level"] == level:
            level_nodes = lvl["nodes"]
            break

    if not level_nodes:
        print(f"[transition] No nodes found at level {level}", file=sys.stderr)
        return

    print(f"[transition] Generating contexts for {len(level_nodes)} node(s) at level {level}...")

    # Purge previous node files
    if nodes_dir.exists():
        for f in nodes_dir.glob("*.md"):
            f.unlink()
    else:
        nodes_dir.mkdir()

    node_descriptions = json.dumps(level_nodes, indent=2)
    slug = graph['slug']

    git_context = f"""
You are working in a git worktree on branch orchestrator/{slug}/<node-id>.
The main repo is at {repo_root}.
Git requires worktrees to be on separate branches — this is expected, not an error.

During development: commit your work to THIS branch (the worktree branch).
During merge: you will merge this branch into the feature branch from the main repo.
To determine the feature branch, run: git -C {repo_root} branch --show-current
"""
    workflow_instructions = f"""
IMPORTANT: The .orchestrator/ directory lives in the MAIN repo, NOT in your worktree.
All state.json updates and addendum writes must target the main repo path:
{repo_root}/.orchestrator/{slug}/

If `{repo_root}/.orchestrator/{slug}/addendums/patches.md` exists, read it at session
start to understand direct fixes applied to the feature branch since your worktree
was created.

During /grill-me, if you discover changes needed outside this node's declared file scope:
- Implement directly if: one-line fix, zero blast radius on other nodes, or test-blocking
  for this node. Document in your addendum under "## Implemented Changes".
- Defer if: multi-file change, touches another node's declared scope, or unclear downstream
  impact. Document in your addendum under "## Deferred Changes".
Always surface both categories to the user with a recommendation before acting.

After all tests pass, update {repo_root}/.orchestrator/{slug}/state.json to set this node's status to "blue".
Then proceed to the merge workflow:
1. cd to the main repo: cd {repo_root}
2. Get the feature branch: git branch --show-current
3. If this is the first completed node at this level: git merge orchestrator/{slug}/<node-id> --no-ff
   Otherwise: rebase first from the worktree, then merge:
   git -C <worktree-path> rebase <feature-branch>
   git merge orchestrator/{slug}/<node-id> --no-ff
4. Re-run all tests
5. If tests pass: update state.json status to "green", then clean up:
   git worktree remove <worktree-path> && git branch -d orchestrator/{slug}/<node-id>
6. If merge conflicts arise: keep status as "blue" and surface conflicts for manual resolution

CRITICAL: Stay in the main repo (cd {repo_root}) for the entire merge + cleanup sequence.
Do NOT cd back to the worktree — it will be removed during cleanup and your shell will
be stuck in a dead directory that breaks all subsequent commands.

DO NOT include a "Co-Authored-By" signature in any commit messages.

If the design requires changes beyond this node's scope, write an addendum to:
{repo_root}/.orchestrator/{slug}/addendums/<node-id>-<description>.md

If merge conflicts occur OR tests fail after merging:
1. Read sibling node addendums: ls {repo_root}/.orchestrator/{slug}/addendums/
   Look at "Implemented Changes" sections — out-of-scope changes by parallel nodes
   may explain the conflict or failure.
2. Apply blast-radius logic to fixes:
   - Small fix, zero blast radius -> implement + document under "Implemented Changes"
   - Large blast radius -> defer + document under "Deferred Changes"
   - Always surface to the user for approval
3. Document in this node's addendum: what failed, what was fixed, what was deferred.
Do NOT read sibling addendums preemptively before merge — only on failure.
"""

    prompt = f"""You are generating implementation context files for nodes in a parallel execution workflow.

Design contract:
---
{contract}
---

Nodes at level {level} that need context files:
---
{node_descriptions}
---

For EACH node, output its context file content between delimiters like this:

===NODE:<node-id>===
<file content>
===END_NODE===

Each node's content MUST begin with this exact line as the very first line:

STOP. Do NOT begin implementing. First, invoke /grill-me — read the skill and ask the user clarifying questions about any ambiguities in design, scope, or implementation approach. Only after ambiguities are resolved, present a plan for the user to review and approve before writing any code.

Then include:

1. **Scope:** The specific section of the design doc this node implements
2. **Constraints:** Files this node may touch, interfaces it must respect, boundaries it must not cross
3. **Dependencies:** What prior work this node builds on
4. **Git context** (include EXACTLY as written):
{git_context}
5. **Workflow instructions** (include EXACTLY as written):
{workflow_instructions}
6. If the node mode is "agent-team", include team composition guidance: the delegator agent should ALWAYS delegate and orchestrate only, never implement. Sub-agents use peer-to-peer messaging.

Output ALL nodes now, each wrapped in ===NODE:<node-id>=== ... ===END_NODE=== delimiters."""

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"[transition] Context generation failed: {result.stderr}", file=sys.stderr)
        else:
            _parse_and_write_nodes(result.stdout, nodes_dir)
            generated = list(nodes_dir.glob("*.md"))
            print(f"[transition] Generated {len(generated)} context file(s)")

    except subprocess.TimeoutExpired:
        print("[transition] Context generation timed out", file=sys.stderr)
    except FileNotFoundError:
        print("[transition] 'claude' CLI not found — is it installed?", file=sys.stderr)


def verify_level_complete(orch_dir: Path, level: int) -> bool:
    """Check that all nodes at the given level are green."""
    graph = json.loads((orch_dir / "graph.json").read_text())
    state = json.loads((orch_dir / "state.json").read_text())

    for lvl in graph["levels"]:
        if lvl["level"] == level:
            for node in lvl["nodes"]:
                ns = state.get("nodes", {}).get(node["id"], {})
                if ns.get("status") != "green":
                    print(f"[transition] Node {node['id']} is not green "
                          f"(status: {ns.get('status', 'unknown')})")
                    return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Orchestrator Level Transition")
    parser.add_argument("orchestrator_dir", help="Path to .orchestrator/<slug>/ directory")
    parser.add_argument("--level", type=int, help="Target level to transition to "
                        "(defaults to current_level + 1)")
    args = parser.parse_args()

    orch_dir = Path(args.orchestrator_dir).resolve()
    state = json.loads((orch_dir / "state.json").read_text())
    current_level = state.get("current_level", 0)
    target_level = args.level if args.level is not None else current_level + 1

    # Verify current level is complete
    if not verify_level_complete(orch_dir, current_level):
        print(f"[transition] Level {current_level} is not complete — cannot proceed",
              file=sys.stderr)
        sys.exit(1)

    print(f"[transition] Transitioning from level {current_level} to level {target_level}")

    # Step 1: Consolidate addendums
    consolidate_addendums(orch_dir)

    # Step 2: Evaluate graph restructuring
    evaluate_graph_restructuring(orch_dir, target_level)

    # Step 3: Generate contexts for next level
    generate_contexts(orch_dir, target_level)

    # Step 3: Update state
    state["current_level"] = target_level
    (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

    print(f"[transition] Level {target_level} is now active")


if __name__ == "__main__":
    main()
