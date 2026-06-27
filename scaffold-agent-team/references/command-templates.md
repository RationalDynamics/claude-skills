# Command templates → `<repo>/.claude/commands/<prefix>-<name>.md`

Each command is YAML frontmatter (`description`) + a markdown body. Fill `{{PLACEHOLDERS}}`.

---

## `<prefix>-team.md` — the orchestrator (primary entry point)

```markdown
---
description: Orchestrate the {{repo}} specialists ({{roles}}) as subagents to work the current task — runs in the desktop app, no terminal or experimental teams needed
---

# /{{prefix}}-team

Run a multi-agent {{repo}} task using **subagents** (the `Agent` tool). Works in the
desktop/web app — no terminal/tmux/experimental teams needed. **You (this session) are
the lead**: scope, dispatch, integrate, enforce the {{ProjectName}} gates, deliver.
Follow `.claude/agents/{{prefix}}-lead.md` and the guardrails in `docs/agent-team.md` + `AGENTS.md`.

Task from the user: **$ARGUMENTS**

## Subagents vs. teams — work within the limits
Subagents are **one-shot**: dispatch → independent run → final message is its report.
They don't message each other or ask follow-ups mid-run. Put everything a specialist needs
into its spawn prompt. Independent specialists run in **parallel** (spawn in one batch);
they inherit your permission mode.

## Preconditions
1. Confirm the intended **{{repo}} worktree** (`git rev-parse --show-toplevel`).
2. If it'll become a branch/PR, ask for the **{{LINEAR_PREFIX}} ID** first.

## Orchestration
1. **Scope it.** Spawn only the roles the task needs. Do **NOT** spawn {{prefix}}-lead — you are the lead.
2. **Plan (blocking).** Dispatch {{prefix}}-architect with the task + {{design doc}} pointers. Wait for its file-level plan.
3. **Implement + test (parallel).** Dispatch {{prefix}}-backend + {{prefix}}-test in one batch (paste the full plan into each). Add {{prefix}}-devops if infra is in scope.
4. **Integrate + verify.** Reconcile diffs yourself. Confirm `{{TYPECHECK_CMD}}` + focused `{{TEST_CMD}}` pass {{+ migration regenerated if schema changed}}. Re-dispatch with feedback if rework is needed.
5. **Deliver.** Summarize the diff + gates (| Task | Specialist | Status | Notes |). Push/PR/deploy are outward — surface for human go-ahead. {{deploy caveat}}.

## Gates (enforce — delegate the fix)
`{{TYPECHECK_CMD}}` green · focused `{{TEST_CMD}}` green · {{migration/invariant rules}} ·
never bypass the pre-commit hook · never {{the never-auto-run deploy actions}} unless explicitly instructed.

> Terminal alternative: with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, the same `{{prefix}}-*`
> roles run as live teammates. Same roster — see `docs/agent-team.md`.
```

---

## `<prefix>-check-progress.md`

```markdown
---
description: Check whether {{ProjectName}} team members are actively working, even before they commit
---

# /{{prefix}}-check-progress

```bash
git diff --stat HEAD
```

| Output | Meaning | Action |
|--------|---------|--------|
| Files with `+/-` | actively working | ✅ wait a cycle |
| Empty | no uncommitted changes | ⚠️ check via `SendMessage` |
| No growth + unresponsive | possibly stuck | ⚠️ `/{{prefix}}-recover-agent` |

`git log` shows only committed work; agents often run a while before committing
({{commit triggers the pre-commit hook → slow}}), so it causes false "stalled" reads.
`git diff --stat HEAD` shows in-progress work immediately.
```

---

## `<prefix>-recover-agent.md`

```markdown
---
description: Safely recover an unresponsive {{ProjectName}} team member without creating a duplicate
---

# /{{prefix}}-recover-agent

Goal: never spawn a duplicate (`backend-2`) while the old one may still be alive.

1. **Verify no active work.** `git diff --stat HEAD`. If files are changing, STOP — it's working.
2. **Graceful shutdown.** `SendMessage` `{"type":"shutdown_request","reason":"unresponsive"}`; wait ~30s.
3. **Stop it.** If no response: `TaskStop` the task (or kill the tmux pane in `teammateMode: tmux`).
4. **Respawn with the SAME name.** Only after the old one is gone: `Agent(subagent_type="{{prefix}}-<role>", name="<same-name>")`.

Spawning before the old instance exits creates duplicates → wasted compute + git conflicts.
```

---

## `<prefix>-project-status.md`

```markdown
---
description: Show the {{ProjectName}} team task board — every task with assignee, status, and blockers
---

# /{{prefix}}-project-status

| # | Task | Assignee | Status | Notes |
|---|------|----------|--------|-------|
| 1 | Implementation plan (files, schema/migration, contract, test plan) | architect | | |
| 2 | Implement change | backend | | |
| 3 | Tests from real schema + invariants | test | | |
| 4 | {{migration if schema changed}} | backend | | |
| 5 | Infra/CI/deploy (if in scope) | devops | | |
| 6 | `{{TYPECHECK_CMD}}` + focused `{{TEST_CMD}}` green | test | | |
| 7 | Deliver: diff summary + gates; human review before push | lead | | |

Status: `pending` · `in-progress` · `blocked` · `done` · `failed`.
Populate from `TaskList`, `git log --oneline --all -20`, `gh run list --limit 5`.
```

---

## `<prefix>-team-status.md`

```markdown
---
description: Show the {{repo}} agent team roster and what each member is currently working on
---

# /{{prefix}}-team-status

| Role | subagent_type | Instance | Model | Current task | Status |
|------|---------------|----------|-------|--------------|--------|
| Team Lead | `{{prefix}}-lead` | `lead` | sonnet | | |
| Architect | `{{prefix}}-architect` | `architect` | opus | | |
| Backend | `{{prefix}}-backend` | `backend` | sonnet | | |
| QA / Test | `{{prefix}}-test` | `test` | sonnet | | |
| DevOps | `{{prefix}}-devops` | `devops` | opus | | |

(Only show roles actually spawned.) Populate from `TaskList`, `git diff --stat HEAD`,
`git log --oneline -10`, or `SendMessage` an instance for a status update.
```
