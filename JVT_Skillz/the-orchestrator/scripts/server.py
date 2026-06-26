#!/usr/bin/env python3
"""
Local HTTP server for The Orchestrator DAG viewer.

Serves the interactive DAG visualization and provides API endpoints
for state polling and level transitions.

Usage:
    python3 server.py <orchestrator-dir>
    python3 server.py .orchestrator/my-feature/

The server runs on localhost:5000 by default (override with --port).
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


class OrchestratorHandler(SimpleHTTPRequestHandler):
    """Handles API requests and serves the viewer HTML."""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._serve_viewer()
        elif parsed.path == "/api/state":
            self._serve_state()
        elif parsed.path == "/api/graph":
            self._serve_graph()
        elif parsed.path == "/api/queue":
            self._serve_queue()
        elif parsed.path == "/api/verify-status":
            self._serve_verify_status()
        elif parsed.path == "/api/verify-instructions":
            self._serve_verify_instructions()
        elif parsed.path == "/assets/orchestrator_logo.svg":
            self._serve_logo()
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/heartbeat/"):
            node_id = parsed.path.split("/api/heartbeat/")[1]
            self._heartbeat_node(node_id)
        elif parsed.path.startswith("/api/state/"):
            node_id = parsed.path.split("/api/state/")[1]
            self._update_node_state(node_id)
        elif parsed.path == "/api/unlock-next-level":
            self._unlock_next_level()
        elif parsed.path == "/api/add-feature":
            self._add_feature()
        elif parsed.path == "/api/update-graph":
            self._update_graph()
        elif parsed.path.startswith("/api/launch/"):
            node_id = parsed.path.split("/api/launch/")[1]
            self._launch_node(node_id)
        elif parsed.path == "/api/patch":
            self._patch()
        elif parsed.path == "/api/verify-level":
            self._verify_level()
        elif parsed.path == "/api/verify-toggle":
            self._verify_toggle()
        elif parsed.path == "/api/verify-instructions":
            self._save_verify_instructions()
        else:
            self.send_error(404)

    def _heartbeat_node(self, node_id):
        """Write/update a heartbeat file for the given node."""
        active_dir = self.server.orchestrator_dir / "active"
        active_dir.mkdir(exist_ok=True)
        heartbeat_file = active_dir / f"{node_id}.heartbeat"
        heartbeat_file.write_text(datetime.now(timezone.utc).isoformat())
        self._send_json({"ok": True})

    def _is_node_locked(self, node_id):
        """Check if a node has a fresh heartbeat (< 10s old)."""
        heartbeat_file = self.server.orchestrator_dir / "active" / f"{node_id}.heartbeat"
        if not heartbeat_file.exists():
            return False
        try:
            ts = datetime.fromisoformat(heartbeat_file.read_text().strip())
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            return age < 10
        except (ValueError, OSError):
            return False

    def _any_node_heartbeat_active(self):
        """Check if any node (excluding __patch__ and __verifier__) has a fresh heartbeat."""
        active_dir = self.server.orchestrator_dir / "active"
        if not active_dir.exists():
            return False
        for hb_file in active_dir.glob("*.heartbeat"):
            if hb_file.stem in ("__patch__", "__verifier__"):
                continue
            try:
                ts = datetime.fromisoformat(hb_file.read_text().strip())
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age < 10:
                    return True
            except (ValueError, OSError):
                continue
        return False

    def _serve_verify_status(self):
        """Return current verification state."""
        orch_dir = self.server.orchestrator_dir
        state = self._read_json("state.json")
        enabled = state.get("verify_enabled", False)
        has_playbook = (orch_dir / "verify" / "instructions.md").exists()

        # Determine status
        status = "pending"
        failures = []
        last_result_path = orch_dir / "verify" / "last_result.json"

        if self._is_node_locked("__verifier__"):
            status = "running"
        elif last_result_path.exists():
            try:
                result_data = json.loads(last_result_path.read_text())
                # Check staleness: if patches.md is newer than last_result.json
                patches_path = orch_dir / "addendums" / "patches.md"
                is_stale = False
                if patches_path.exists():
                    patches_mtime = patches_path.stat().st_mtime
                    result_mtime = last_result_path.stat().st_mtime
                    if patches_mtime > result_mtime:
                        is_stale = True

                if is_stale:
                    status = "stale"
                elif result_data.get("passed"):
                    status = "passed"
                else:
                    status = "failed"
                    failures = result_data.get("failures", [])
            except (json.JSONDecodeError, OSError):
                status = "pending"

        self._send_json({
            "enabled": enabled,
            "has_playbook": has_playbook,
            "status": status,
            "failures": failures,
        })

    def _serve_verify_instructions(self):
        """Return current verify/instructions.md content."""
        instructions_path = self.server.orchestrator_dir / "verify" / "instructions.md"
        if instructions_path.exists():
            self._send_json({"content": instructions_path.read_text(), "exists": True})
        else:
            self._send_json({"content": "", "exists": False})

    def _save_verify_instructions(self):
        """Save content to verify/instructions.md."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        verify_dir = self.server.orchestrator_dir / "verify"
        verify_dir.mkdir(exist_ok=True)
        (verify_dir / "instructions.md").write_text(body.get("content", ""))
        self._send_json({"ok": True})

    def _verify_toggle(self):
        """Toggle verify_enabled in state.json."""
        state = self._read_json("state.json")
        current = state.get("verify_enabled", False)
        state["verify_enabled"] = not current
        self._write_json("state.json", state)
        self._send_json({"ok": True, "enabled": state["verify_enabled"]})

    def _verify_level(self):
        """Launch the two-step verification process."""
        orch_dir = self.server.orchestrator_dir
        state = self._read_json("state.json")
        graph = self._read_json("graph.json")

        # Validate: verify_enabled
        if not state.get("verify_enabled", False):
            self._send_json({"ok": False, "error": "Verifier is not enabled"})
            return

        # Validate: instructions.md exists
        instructions_path = orch_dir / "verify" / "instructions.md"
        if not instructions_path.exists():
            self._send_json({"ok": False, "error": "No verification playbook found"})
            return

        # Validate: no transition running
        if state.get("transition_status") == "running":
            self._send_json({"ok": False, "error": "A level transition is in progress"})
            return

        # Validate: __verifier__ heartbeat not active
        if self._is_node_locked("__verifier__"):
            self._send_json({"ok": False, "error": "Verification already in progress"})
            return

        # Validate: __patch__ heartbeat not active
        if self._is_node_locked("__patch__"):
            self._send_json({"ok": False, "error": "Patch in progress — cannot verify"})
            return

        # Validate: all current-level nodes are green
        current_level = state.get("current_level", 0)
        current_nodes = self._nodes_at_level(graph, current_level)
        for node in current_nodes:
            node_state = state["nodes"].get(node["id"], {})
            if node_state.get("status") != "green":
                self._send_json({
                    "ok": False,
                    "error": f"Node {node['id']} is not green (status: {node_state.get('status', 'unknown')})"
                })
                return

        # Set verification_status to running
        state["verification_status"] = "running"
        self._write_json("state.json", state)

        # Run verification in background thread
        repo_root = self._find_repo_root(orch_dir)
        thread = threading.Thread(
            target=self._run_verification,
            args=(orch_dir, repo_root),
            daemon=True,
        )
        thread.start()

        self._send_json({"ok": True})

    def _run_verification(self, orch_dir, repo_root):
        """Background thread: update playbook then launch evaluator terminal."""
        try:
            # Step 1: Update playbook synchronously
            self._update_verify_playbook(orch_dir)

            # Step 2: Launch evaluator terminal
            self._launch_verifier_terminal(orch_dir, repo_root)

        except Exception as e:
            print(f"[orchestrator] Verification launch failed: {e}", file=sys.stderr)
            try:
                state = json.loads((orch_dir / "state.json").read_text())
                state["verification_status"] = None
                (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
            except Exception as write_err:
                print(f"[orchestrator] Failed to write error state: {write_err}", file=sys.stderr)

    def _update_verify_playbook(self, orch_dir):
        """Step 1: Update verification playbook with context from completed level."""
        instructions_path = orch_dir / "verify" / "instructions.md"
        current_instructions = instructions_path.read_text()

        # Read addendums
        addendums_dir = orch_dir / "addendums"
        addendum_content = ""
        if addendums_dir.exists():
            for f in sorted(addendums_dir.glob("*.md")):
                if f.name == "patches.md":
                    continue
                addendum_content += f"## Addendum: {f.stem}\n\n{f.read_text()}\n\n"

        # Read patches
        patches_path = addendums_dir / "patches.md" if addendums_dir.exists() else orch_dir / "addendums" / "patches.md"
        patches_content = ""
        if patches_path.exists():
            patches_content = patches_path.read_text()

        # Read contract
        contract = (orch_dir / "contract.md").read_text()

        prompt = f"""You are updating a verification playbook for an implementation project.

Current playbook:
---
{current_instructions}
---

Features completed at this level (from addendums):
---
{addendum_content if addendum_content else "(none)"}
---

Patches applied:
---
{patches_content if patches_content else "(none)"}
---

Updated design contract:
---
{contract}
---

Update the playbook to include verification steps for the features just completed.
Build on existing steps — do not remove verification for previously completed features.
Each step should be concrete and executable: specific URLs to visit, elements to check,
API calls to make, expected responses.

Output the complete updated playbook between delimiters:
===UPDATED_INSTRUCTIONS===
<complete instructions.md content>
===END_INSTRUCTIONS==="""

        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )

        if result.returncode != 0:
            print(f"[orchestrator] Playbook update failed (code {result.returncode}): {result.stderr[:300]}", file=sys.stderr)
            return  # Continue with existing instructions

        import re
        match = re.search(r'===UPDATED_INSTRUCTIONS===\s*\n(.*?)===END_INSTRUCTIONS===', result.stdout, re.DOTALL)
        if match:
            instructions_path.write_text(match.group(1).strip())
            print("[orchestrator] Verification playbook updated", file=sys.stderr)
        else:
            print("[orchestrator] Warning: could not parse updated playbook — keeping existing", file=sys.stderr)

    def _launch_verifier_terminal(self, orch_dir, repo_root):
        """Step 2: Launch evaluator terminal with skeptical QA prompt."""
        server_port = self.server.server_address[1]

        # Write verify prompt file
        verify_prompt_file = orch_dir / "_verify_prompt.md"
        verify_prompt_file.write_text(f"""STOP. You are a skeptical QA evaluator. Assume the application is broken until proven
otherwise. Your job is to observe and report — do NOT fix anything.

Read the verification playbook at {orch_dir}/verify/instructions.md and execute each
step. For each step:
1. Run the command or check described
2. Evaluate the result critically — look for partial failures, wrong data, missing elements
3. Record pass or fail with details

After completing all steps, write results to {orch_dir}/verify/last_result.json:
{{
  "passed": true/false,
  "timestamp": "<ISO-8601>",
  "failures": [
    {{"step": "<step description>", "error": "<what went wrong>", "suggestion": "<possible cause>"}}
  ]
}}

If all steps pass, set "passed": true and "failures": [].
If any step fails, set "passed": false and list all failures.

Do NOT attempt to fix failures. Report them and stop.
""")

        # Build .command script
        script_content = f"""#!/bin/bash -l
export ORCHESTRATOR_SESSION=1
PORT={server_port}
NODE_ID=__verifier__
(while true; do curl -s -X POST http://localhost:${{PORT}}/api/heartbeat/${{NODE_ID}} > /dev/null 2>&1; sleep 3; done) &
HEARTBEAT_PID=$!
trap "kill $HEARTBEAT_PID 2>/dev/null" EXIT

cd "{repo_root}"
claude --permission-mode plan "$(cat '{verify_prompt_file}')"
"""

        launch_dir = repo_root / ".worktrees"
        launch_dir.mkdir(parents=True, exist_ok=True)
        script_path = launch_dir / "launch-verifier.command"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        subprocess.run(["open", str(script_path)], check=True)
        print("[orchestrator] Verifier terminal launched", file=sys.stderr)

    def _patch(self):
        """Launch a patch/fast-fix terminal session on the feature branch."""
        orch_dir = self.server.orchestrator_dir

        # Validate: no active node heartbeats
        if self._any_node_heartbeat_active():
            self._send_json({
                "ok": False,
                "error": "Cannot patch while node sessions are active. Close all terminal sessions first."
            })
            return

        # Validate: no active patch heartbeat
        if self._is_node_locked("__patch__"):
            self._send_json({"ok": False, "error": "A patch is already in progress"})
            return

        # Validate: no active verifier heartbeat
        if self._is_node_locked("__verifier__"):
            self._send_json({"ok": False, "error": "Verification in progress — cannot patch"})
            return

        # Validate: no transition running
        state = self._read_json("state.json")
        if state.get("transition_status") == "running":
            self._send_json({"ok": False, "error": "A level transition is in progress"})
            return

        repo_root = self._find_repo_root(orch_dir)
        graph = self._read_json("graph.json")
        slug = graph["slug"]

        # Write prompt file
        prompt_file = orch_dir / "_patch_prompt.md"
        prompt_file.write_text(f"""STOP. Do NOT begin implementing. First, invoke /grill-me — read the skill and ask the user clarifying questions about what needs to be patched and why. Only after the fix is clear, present a plan for the user to review and approve before writing any code.

You are making a quick patch/fix directly on the feature branch.

Read the orchestrator state for context:
- {orch_dir}/contract.md (design document)
- {orch_dir}/graph.json (current DAG structure)
- {orch_dir}/state.json (node statuses)
- {orch_dir}/addendums/ (any existing addendums)

If `{repo_root}/.orchestrator/{slug}/addendums/patches.md` exists, read it at session
start to understand prior patches applied to the feature branch.

The user will describe what needs to be fixed. Implement the fix on the current branch.

After implementing, append to {orch_dir}/addendums/patches.md (create if it doesn't exist).
Use this format for each patch entry:

## Patch: <short description> — <current ISO-8601 timestamp>
**Files changed:** `path/to/file`
**Change:** <what was changed>
**Reason:** <why this was needed>
**Commit:** <short hash after committing>

DO NOT include a "Co-Authored-By" signature in commit messages.
""")

        # Build .command script
        server_port = self.server.server_address[1]
        script_content = f"""#!/bin/bash -l
export ORCHESTRATOR_SESSION=1
PORT={server_port}
NODE_ID=__patch__
(while true; do curl -s -X POST http://localhost:${{PORT}}/api/heartbeat/${{NODE_ID}} > /dev/null 2>&1; sleep 3; done) &
HEARTBEAT_PID=$!
trap "kill $HEARTBEAT_PID 2>/dev/null" EXIT

cd "{repo_root}"
claude --permission-mode plan "$(cat '{prompt_file}')"
"""

        launch_dir = repo_root / ".worktrees"
        launch_dir.mkdir(parents=True, exist_ok=True)
        script_path = launch_dir / "launch-patch.command"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        try:
            subprocess.run(["open", str(script_path)], check=True)
            self._send_json({"ok": True})
        except subprocess.CalledProcessError as e:
            self._send_json({"ok": False, "error": str(e)})

    def _serve_queue(self):
        """Scan addendums/ for user_request_*.md files and return parsed list."""
        import re as _re
        addendums_dir = self.server.orchestrator_dir / "addendums"
        items = []
        if addendums_dir.exists():
            for f in sorted(addendums_dir.glob("user_request_*.md")):
                title = f.stem
                summary = "No summary"
                try:
                    text = f.read_text()
                    # Parse title from first H1: # User Request: <Title>
                    title_match = _re.search(r'^#\s+User Request:\s*(.+)$', text, _re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                    # Parse summary: first paragraph after ## Summary
                    summary_match = _re.search(r'^##\s+Summary\s*\n+(.+?)(?:\n\n|\n##|\Z)', text, _re.MULTILINE | _re.DOTALL)
                    if summary_match:
                        summary = summary_match.group(1).strip()
                except Exception:
                    pass
                items.append({"filename": f.name, "title": title, "summary": summary})
        self._send_json({"items": items, "count": len(items)})

    def _serve_viewer(self):
        viewer_path = Path(__file__).parent.parent / "assets" / "viewer.html"
        content = viewer_path.read_text()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())

    def _serve_logo(self):
        logo_path = Path(__file__).parent.parent / "assets" / "orchestrator_logo.svg"
        content = logo_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.end_headers()
        self.wfile.write(content)

    def _serve_state(self):
        state = self._read_json("state.json")
        # Compute locked status on-the-fly from heartbeat files
        for node_id in state.get("nodes", {}):
            state["nodes"][node_id]["locked"] = self._is_node_locked(node_id)
        state["patch_locked"] = self._is_node_locked("__patch__")
        # Add verification fields (backwards compatible defaults)
        state.setdefault("verify_enabled", False)
        state.setdefault("verification_status", None)
        self._send_json(state)

    def _serve_graph(self):
        graph = self._read_json("graph.json")
        self._send_json(graph)

    def _update_node_state(self, node_id):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        state = self._read_json("state.json")
        if node_id not in state.get("nodes", {}):
            self.send_error(404, f"Node {node_id} not found")
            return

        node_state = state["nodes"][node_id]
        if "status" in body:
            node_state["status"] = body["status"]
        if "worktree_path" in body:
            node_state["worktree_path"] = body["worktree_path"]
        if body.get("status") == "blue" and not node_state.get("completed_at"):
            node_state["completed_at"] = datetime.now(timezone.utc).isoformat()
        if body.get("status") == "red" and not node_state.get("started_at"):
            node_state["started_at"] = datetime.now(timezone.utc).isoformat()

        self._write_json("state.json", state)
        self._send_json({"ok": True})

    def _unlock_next_level(self):
        state = self._read_json("state.json")
        graph = self._read_json("graph.json")
        current_level = state.get("current_level", 0)

        # Reject if a transition is already running
        if state.get("transition_status") == "running":
            self._send_json({"ok": False, "error": "Level transition already in progress"})
            return

        # Verify all nodes at current level are green
        current_nodes = self._nodes_at_level(graph, current_level)
        for node in current_nodes:
            node_state = state["nodes"].get(node["id"], {})
            if node_state.get("status") != "green":
                self._send_json({
                    "ok": False,
                    "error": f"Node {node['id']} is not green (status: {node_state.get('status', 'unknown')})"
                })
                return

        next_level = current_level + 1
        max_level = max(lvl["level"] for lvl in graph["levels"])
        if next_level > max_level:
            self._send_json({"ok": False, "error": "All levels complete"})
            return

        # Mark transition as running (current_level stays unchanged until success)
        state["transition_status"] = "running"
        state["transition_error"] = None
        self._write_json("state.json", state)

        # Run level transition in background thread
        orch_dir = self.server.orchestrator_dir
        slug = graph["slug"]
        thread = threading.Thread(
            target=self._run_level_transition,
            args=(orch_dir, slug, next_level),
            daemon=True,
        )
        thread.start()

        self._send_json({"ok": True, "next_level": next_level, "message": "Level transition started"})

    def _run_level_transition(self, orch_dir, slug, next_level):
        """Run contract update and context generation for the next level."""
        try:
            self._run_level_transition_inner(orch_dir, slug, next_level)

            # Clear any queued user requests after successful transition
            addendums_dir = orch_dir / "addendums"
            if addendums_dir.exists():
                for qf in addendums_dir.glob("user_request_*.md"):
                    qf.unlink()

            # Success — advance the level and mark complete
            state = json.loads((orch_dir / "state.json").read_text())
            state["current_level"] = next_level
            state["transition_status"] = "complete"
            state["transition_error"] = None
            state["transition_phase"] = None
            (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
            print(f"[orchestrator] Level transition to {next_level} complete", file=sys.stderr)

        except Exception as e:
            # Failure — keep current_level unchanged, mark failed
            print(f"[orchestrator] Level transition failed: {e}", file=sys.stderr)
            try:
                state = json.loads((orch_dir / "state.json").read_text())
                state["transition_status"] = "failed"
                state["transition_error"] = str(e)
                state["transition_phase"] = None
                (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
            except Exception as write_err:
                print(f"[orchestrator] Failed to write error state: {write_err}", file=sys.stderr)

    def _run_level_transition_inner(self, orch_dir, slug, next_level):
        """Inner transition logic. Raises on failure."""
        # Clean up stale heartbeat files from the completed level
        active_dir = orch_dir / "active"
        if active_dir.exists():
            for f in active_dir.glob("*.heartbeat"):
                f.unlink()

        addendums_dir = orch_dir / "addendums"
        has_addendums = addendums_dir.exists() and any(addendums_dir.iterdir())

        # Set transition phase: consolidating
        state = json.loads((orch_dir / "state.json").read_text())
        state["transition_phase"] = "consolidating"
        (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

        # Step 1: Consolidate addendums if any exist
        if has_addendums:
            addendum_files = list(addendums_dir.glob("*.md"))
            addendum_content = ""
            for f in addendum_files:
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

            result = subprocess.run(
                ["claude", "-p", "--model", "opus"],
                input=prompt,
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Contract update failed (code {result.returncode}): {result.stderr[:300]}")
            if not result.stdout.strip():
                raise RuntimeError("Contract update returned empty output")

            import re
            match = re.search(r'===UPDATED_CONTRACT===\s*\n(.*?)===END_CONTRACT===',
                              result.stdout, re.DOTALL)
            if match:
                contract_path.write_text(match.group(1).strip())
            else:
                raise RuntimeError("Contract update output missing ===UPDATED_CONTRACT=== delimiters")

            # Purge addendums
            for f in addendum_files:
                f.unlink()

        # Step 2: Evaluate graph restructuring
        state = json.loads((orch_dir / "state.json").read_text())
        state["transition_phase"] = "restructuring"
        (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

        self._evaluate_graph_restructuring(orch_dir, slug, next_level)

        # Step 3: Generate node contexts for next level
        state = json.loads((orch_dir / "state.json").read_text())
        state["transition_phase"] = "generating"
        (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

        self._generate_node_contexts(orch_dir, next_level)

    def _evaluate_graph_restructuring(self, orch_dir, slug, next_level):
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
- New nodes may only be placed at level {next_level} or higher
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

        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"[orchestrator] Graph restructuring evaluation failed (code {result.returncode}): {result.stderr[:300]}", file=sys.stderr)
            return False

        output = result.stdout.strip()

        if "===NO_RESTRUCTURING_NEEDED===" in output:
            print("[orchestrator] No graph restructuring needed", file=sys.stderr)
            return False

        match = re.search(r'===RESTRUCTURED_GRAPH===\s*\n(.*?)===END_RESTRUCTURED_GRAPH===', output, re.DOTALL)
        if not match:
            print("[orchestrator] Warning: ambiguous restructuring output — skipping", file=sys.stderr)
            return False

        try:
            new_graph = json.loads(match.group(1).strip())
        except json.JSONDecodeError as e:
            print(f"[orchestrator] Warning: invalid JSON in restructured graph — skipping: {e}", file=sys.stderr)
            return False

        # Validate the restructured graph
        self._validate_restructured_graph(graph, new_graph, immutable_ids)

        # Write the new graph
        (orch_dir / "graph.json").write_text(json.dumps(new_graph, indent=2))
        print("[orchestrator] Graph restructured successfully", file=sys.stderr)

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

    def _validate_restructured_graph(self, old_graph, new_graph, immutable_ids):
        """Validate that a restructured graph preserves immutable nodes and structural rules."""
        # Build lookup for new graph nodes
        new_nodes = {}
        for lvl in new_graph["levels"]:
            for node in lvl["nodes"]:
                new_nodes[node["id"]] = {"node": node, "level": lvl["level"]}

        # Every immutable node must exist with same id and level
        old_nodes = {}
        for lvl in old_graph["levels"]:
            for node in lvl["nodes"]:
                old_nodes[node["id"]] = {"node": node, "level": lvl["level"]}

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

    def _generate_node_contexts(self, orch_dir, level):
        """Generate context files for nodes at the given level."""
        graph = json.loads((orch_dir / "graph.json").read_text())
        contract = (orch_dir / "contract.md").read_text()
        repo_root = self._find_repo_root(orch_dir)
        nodes_dir = orch_dir / "nodes"

        # Purge previous level's node files
        if nodes_dir.exists():
            for f in nodes_dir.glob("*.md"):
                f.unlink()
        else:
            nodes_dir.mkdir()

        level_nodes = self._nodes_at_level(graph, level)
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

        # Generate each node's context via a single claude -p call.
        # Use delimiters so we can parse the output and write files in Python.
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

        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Context generation failed (code {result.returncode}): {result.stderr[:300]}")
        if not result.stdout.strip():
            raise RuntimeError("Context generation returned empty output")

        self._parse_and_write_nodes(result.stdout, nodes_dir)

        # Verify all expected node files were created
        expected = {n["id"] for n in level_nodes}
        created = {f.stem for f in nodes_dir.glob("*.md")}
        missing = expected - created
        if missing:
            raise RuntimeError(f"Context generation missing nodes: {missing}")

    def _launch_node(self, node_id):
        """Launch a terminal session for a node."""
        graph = self._read_json("graph.json")
        state = self._read_json("state.json")
        orch_dir = self.server.orchestrator_dir

        node = self._find_node(graph, node_id)
        if not node:
            self._send_json({"ok": False, "error": f"Node {node_id} not found"})
            return

        node_state = state["nodes"].get(node_id, {})
        context_file = orch_dir / "nodes" / f"{node_id}.md"
        repo_root = self._find_repo_root(orch_dir)

        if node_state.get("status") == "green":
            self._send_json({"ok": False, "error": "Node already complete"})
            return

        # Check if node has an active session
        if self._is_node_locked(node_id):
            self._send_json({"ok": False, "error": "Node has an active session"})
            return

        # Check if a patch is in progress
        if self._is_node_locked("__patch__"):
            self._send_json({"ok": False, "error": "Patch in progress — node launches blocked"})
            return

        # Determine worktree path
        worktree_dir = repo_root / ".worktrees" / node_id
        branch_name = f"orchestrator/{graph['slug']}/{node_id}"

        # Build the launch script
        commands = []

        if not worktree_dir.exists():
            commands.append(f'cd "{repo_root}"')
            commands.append(f'git worktree add ".worktrees/{node_id}" -b "{branch_name}"')

        commands.append(f'cd "{worktree_dir}"')

        # Update state
        node_state["status"] = "red"
        node_state["started_at"] = datetime.now(timezone.utc).isoformat()
        node_state["worktree_path"] = str(worktree_dir)
        state["nodes"][node_id] = node_state
        self._write_json("state.json", state)

        if context_file.exists():
            commands.append(
                f'claude --permission-mode plan "$(cat \'{context_file}\')"'
            )
        else:
            commands.append("claude")

        # Write a .command file and open it — macOS launches it in
        # Terminal.app natively with no Automation permission needed.
        launch_dir = repo_root / ".worktrees"
        launch_dir.mkdir(parents=True, exist_ok=True)
        script_path = launch_dir / f"launch-{node_id}.command"
        shell_script = "\n".join(commands)
        server_port = self.server.server_address[1]
        heartbeat_preamble = (
            f"PORT={server_port}\n"
            f"NODE_ID={node_id}\n"
            "(while true; do curl -s -X POST http://localhost:${PORT}/api/heartbeat/${NODE_ID} > /dev/null 2>&1; sleep 3; done) &\n"
            "HEARTBEAT_PID=$!\n"
            'trap "kill $HEARTBEAT_PID 2>/dev/null" EXIT\n'
        )
        script_path.write_text(f"#!/bin/bash -l\nexport ORCHESTRATOR_SESSION=1\n{heartbeat_preamble}\n{shell_script}\n")
        script_path.chmod(0o755)

        try:
            subprocess.run(["open", str(script_path)], check=True)
            self._send_json({"ok": True, "worktree": str(worktree_dir)})
        except subprocess.CalledProcessError as e:
            self._send_json({"ok": False, "error": str(e)})

    def _add_feature(self):
        """Launch a terminal session for speccing a new feature request."""
        orch_dir = self.server.orchestrator_dir
        repo_root = self._find_repo_root(orch_dir)
        graph = self._read_json("graph.json")
        slug = graph["slug"]

        # Write the prompt to a temp file so it can be cat'd in the .command script
        prompt_path = orch_dir / "_add_feature_prompt.md"
        prompt_path.write_text(f"""You are helping the user spec out a new feature or requirement for an active orchestration.

First, read the current orchestrator state to understand the project:
- Contract: {orch_dir}/contract.md
- Graph: {orch_dir}/graph.json
- State: {orch_dir}/state.json
- Existing addendums: ls {orch_dir}/addendums/

Use /grill-me to help the user fully spec out their feature or request. Ask clarifying questions
about scope, priority, affected areas, and how it relates to existing nodes.

Once the spec is complete, write the result to:
{orch_dir}/addendums/user_request_<short-kebab-description>.md

Use this exact format:

# User Request: <Title>

## Summary
<1-2 sentence summary of the feature/request>

## Specification
<Detailed specification of what needs to be implemented>

## Priority
<high | medium | low — with brief justification>

## Affected Areas
<Which parts of the codebase / which existing or future nodes this affects>
""")

        # Build .command script following the same pattern as _launch_node
        launch_dir = repo_root / ".worktrees"
        launch_dir.mkdir(parents=True, exist_ok=True)
        script_path = launch_dir / "launch-add-feature.command"
        script_path.write_text(
            f'#!/bin/bash -l\n'
            f'export ORCHESTRATOR_SESSION=1\n'
            f'cd "{repo_root}"\n'
            f'claude --permission-mode plan "$(cat \'{prompt_path}\')"\n'
        )
        script_path.chmod(0o755)

        try:
            subprocess.run(["open", str(script_path)], check=True)
            self._send_json({"ok": True})
        except subprocess.CalledProcessError as e:
            self._send_json({"ok": False, "error": str(e)})

    def _update_graph(self):
        """Trigger mid-level graph restructuring to incorporate queued features."""
        orch_dir = self.server.orchestrator_dir
        state = self._read_json("state.json")
        graph = self._read_json("graph.json")
        slug = graph["slug"]

        # Validate: no transition already running
        if state.get("transition_status") == "running":
            self._send_json({"ok": False, "error": "A transition is already running"})
            return

        # Validate: queue is non-empty
        addendums_dir = orch_dir / "addendums"
        queue_files = list(addendums_dir.glob("user_request_*.md")) if addendums_dir.exists() else []
        if not queue_files:
            self._send_json({"ok": False, "error": "Feature queue is empty"})
            return

        # Validate: not all current-level nodes are green
        current_level = state.get("current_level", 0)
        current_nodes = self._nodes_at_level(graph, current_level)
        all_green = all(
            state["nodes"].get(n["id"], {}).get("status") == "green"
            for n in current_nodes
        )
        if all_green:
            self._send_json({"ok": False, "error": "All current-level nodes are green — use Unlock Next Level instead"})
            return

        # Set transition status
        state["transition_status"] = "running"
        state["transition_phase"] = "restructuring"
        state["transition_error"] = None
        self._write_json("state.json", state)

        # Spawn background thread
        thread = threading.Thread(
            target=self._run_graph_update,
            args=(orch_dir, slug),
            daemon=True,
        )
        thread.start()

        self._send_json({"ok": True})

    def _run_graph_update(self, orch_dir, slug):
        """Background thread: restructure graph to incorporate queued user requests."""
        try:
            self._run_graph_update_inner(orch_dir, slug)

            # Success
            state = json.loads((orch_dir / "state.json").read_text())
            state["transition_status"] = "complete"
            state["transition_phase"] = None
            state["transition_error"] = None
            (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
            print("[orchestrator] Graph update complete", file=sys.stderr)

        except Exception as e:
            print(f"[orchestrator] Graph update failed: {e}", file=sys.stderr)
            try:
                state = json.loads((orch_dir / "state.json").read_text())
                state["transition_status"] = "failed"
                state["transition_error"] = str(e)
                state["transition_phase"] = None
                (orch_dir / "state.json").write_text(json.dumps(state, indent=2))
            except Exception as write_err:
                print(f"[orchestrator] Failed to write error state: {write_err}", file=sys.stderr)

    def _run_graph_update_inner(self, orch_dir, slug):
        """Inner graph update logic. Raises on failure."""
        import re as _re

        addendums_dir = orch_dir / "addendums"
        queue_files = list(addendums_dir.glob("user_request_*.md"))

        # Read all user request files
        request_content = ""
        for f in queue_files:
            request_content += f"### {f.stem}\n\n{f.read_text()}\n\n"

        graph = json.loads((orch_dir / "graph.json").read_text())
        contract = (orch_dir / "contract.md").read_text()
        state = json.loads((orch_dir / "state.json").read_text())
        current_level = state.get("current_level", 0)

        # Build immutable set: green + blue node IDs
        immutable_ids = set()
        for node_id, ns in state.get("nodes", {}).items():
            if ns.get("status") in ("green", "blue"):
                immutable_ids.add(node_id)

        immutable_list = ", ".join(sorted(immutable_ids)) if immutable_ids else "(none)"

        prompt = f"""You are restructuring a DAG graph to incorporate new user-requested features.

Current graph.json:
---
{json.dumps(graph, indent=2)}
---

Current contract/design document:
---
{contract}
---

New user requests to incorporate:
---
{request_content}
---

Immutable node IDs (status green or blue — MUST NOT be modified or removed):
{immutable_list}

Current level: {current_level}

Restructure the graph to accommodate these new user requests. Consider:
- Adding new nodes for the requested features
- Splitting existing red nodes if they now need to cover more scope
- Merging red nodes if requests overlap with existing planned work
- Removing red nodes that are superseded by the new requests

Rules:
- Immutable nodes (listed above) must remain exactly as they are — same id, same level, same fields
- New nodes may be placed at level {current_level} or higher
- No two nodes at the same level may have overlapping files
- The top-level "slug" and "repo_root" fields must be preserved exactly
- All node dependencies must reference existing nodes at strictly lower levels
- Every node must have: id, name, description, files (array), dependencies (array), mode

Output the complete restructured graph.json:
===RESTRUCTURED_GRAPH===
<the complete updated graph.json>
===END_RESTRUCTURED_GRAPH==="""

        result = subprocess.run(
            ["claude", "-p", "--model", "opus"],
            input=prompt,
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Graph update failed (code {result.returncode}): {result.stderr[:300]}")

        output = result.stdout.strip()
        match = _re.search(r'===RESTRUCTURED_GRAPH===\s*\n(.*?)===END_RESTRUCTURED_GRAPH===', output, _re.DOTALL)
        if not match:
            raise RuntimeError("Graph update returned no restructured graph")

        try:
            new_graph = json.loads(match.group(1).strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in restructured graph: {e}")

        # Validate
        self._validate_restructured_graph(graph, new_graph, immutable_ids)

        # Write the new graph
        (orch_dir / "graph.json").write_text(json.dumps(new_graph, indent=2))
        print("[orchestrator] Graph restructured for queued features", file=sys.stderr)

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

        for node_id in new_node_ids - old_node_ids:
            state["nodes"][node_id] = {"status": "red"}

        for node_id in old_node_ids - new_node_ids:
            if state["nodes"].get(node_id, {}).get("status") == "red":
                del state["nodes"][node_id]

        (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

        # Step 2: Regenerate node contexts if the current level was affected
        current_level = state.get("current_level", 0)
        old_current = {n["id"]: n for lvl in graph["levels"] if lvl["level"] == current_level for n in lvl["nodes"]}
        new_current = {n["id"]: n for lvl in new_graph["levels"] if lvl["level"] == current_level for n in lvl["nodes"]}

        current_level_changed = old_current != new_current
        if current_level_changed:
            state = json.loads((orch_dir / "state.json").read_text())
            state["transition_phase"] = "generating"
            (orch_dir / "state.json").write_text(json.dumps(state, indent=2))

            self._generate_node_contexts(orch_dir, current_level)
            print(f"[orchestrator] Regenerated contexts for level {current_level}", file=sys.stderr)

        # Clear the queue
        for f in queue_files:
            f.unlink()

    @staticmethod
    def _parse_and_write_nodes(output, nodes_dir):
        """Parse delimited node content from claude output and write files."""
        import re
        pattern = r'===NODE:([^=]+)===\s*\n(.*?)===END_NODE==='
        matches = re.findall(pattern, output, re.DOTALL)
        if not matches:
            print(f"[orchestrator] Warning: no node delimiters found in output", file=sys.stderr)
            return
        for node_id, content in matches:
            node_id = node_id.strip()
            file_path = nodes_dir / f"{node_id}.md"
            file_path.write_text(content.strip() + "\n")
            print(f"[orchestrator] Wrote {file_path}")

    def _find_repo_root(self, start_path):
        """Walk up from start_path to find the git repo root."""
        path = Path(start_path).resolve()
        while path != path.parent:
            if (path / ".git").exists():
                return path
            path = path.parent
        return Path(start_path).resolve().parent

    def _nodes_at_level(self, graph, level):
        for lvl in graph["levels"]:
            if lvl["level"] == level:
                return lvl["nodes"]
        return []

    def _find_node(self, graph, node_id):
        for lvl in graph["levels"]:
            for node in lvl["nodes"]:
                if node["id"] == node_id:
                    return node
        return None

    def _read_json(self, filename):
        path = self.server.orchestrator_dir / filename
        return json.loads(path.read_text())

    def _write_json(self, filename, data):
        path = self.server.orchestrator_dir / filename
        path.write_text(json.dumps(data, indent=2))

    def _send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Quiet logging — only errors
        if args and "404" not in str(args[0]):
            return
        super().log_message(format, *args)


class OrchestratorServer(HTTPServer):
    def __init__(self, orchestrator_dir, port=5000):
        self.orchestrator_dir = Path(orchestrator_dir).resolve()
        super().__init__(("localhost", port), OrchestratorHandler)


def main():
    parser = argparse.ArgumentParser(description="The Orchestrator DAG Viewer Server")
    parser.add_argument("orchestrator_dir", help="Path to .orchestrator/<slug>/ directory")
    parser.add_argument("--port", type=int, default=5000, help="Port to serve on (default: 5000)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    orch_dir = Path(args.orchestrator_dir)
    if not (orch_dir / "graph.json").exists():
        print(f"Error: {orch_dir}/graph.json not found", file=sys.stderr)
        sys.exit(1)

    server = OrchestratorServer(orch_dir, args.port)
    url = f"http://localhost:{args.port}"
    print(f"[orchestrator] Serving at {url}")
    print(f"[orchestrator] Watching: {orch_dir}")

    if not args.no_open:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[orchestrator] Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
