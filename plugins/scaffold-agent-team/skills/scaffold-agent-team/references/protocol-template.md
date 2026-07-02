# Protocol template → `<repo>/docs/agent-team.md`

Fill every `{{PLACEHOLDER}}` from the extraction step. Delete roles you didn't pick.

---

```markdown
# {{ProjectName}} Agent Team — Coordination Protocol

A lightweight multi-agent "team" for working on **{{repo}}** ({{stack one-liner}},
deployed to {{deploy target}}). Adapted from the scry-team / dis-team pattern; tuned
for {{repo}}'s stack and rules.

This file is the canonical protocol. The `/{{prefix}}-team` command and the
`{{prefix}}-*` agents (`.claude/agents/{{prefix}}-*.md`) reference it. It is
**opt-in** — nothing here runs unless you invoke `/{{prefix}}-team`.

> Read `AGENTS.md` (repo guide){{, + design doc at <path>}} before touching a subsystem.

## Roster

| Role | subagent_type | instance `name` | Model | Owns |
|------|---------------|-----------------|-------|------|
| Team Lead | `{{prefix}}-lead` | `lead` (the orchestrator — that's you) | sonnet | coordination, task board, gate enforcement. No code. |
| Architect | `{{prefix}}-architect` | `architect` | fable (xhigh) | reads {{design doc}} + AGENTS.md + code, produces a file-level plan, answers design questions. No app code. |
| Backend | `{{prefix}}-backend` | `backend` | sonnet | {{the impl surface: frameworks, data layer, migrations, workers}}. |
| QA / Test | `{{prefix}}-test` | `test` | sonnet | {{test runner}} against {{real deps}}, fixtures from the real schema, {{invariant}} coverage, {{typecheck}}. |
| Reviewer | `{{prefix}}-reviewer` | `reviewer` (one-shot — spawn per review, never a standing teammate) | fable (xhigh) | fresh-context review of the integrated diff vs the plan; correctness-affecting findings only. Read-only. |
| DevOps | `{{prefix}}-devops` | `devops` | sonnet | {{infra: Terraform/CI/Cloud Run/secrets}}. Enforces deploy discipline. |

**Forbidden:** never spawn a second lead; never create duplicate instances
(`backend-2`); reuse an instance by passing the same `name`.

## Effort scaling (the lead decides the tier first)

- **Trivial** — diff describable in one sentence; no schema/API/infra impact → skip
  the team entirely; solo is faster and cheaper.
- **Routine** — one subsystem, no migration, no security surface → architect →
  backend + test (parallel) → one reviewer pass on the integrated diff.
- **Large/risky** — multi-subsystem, {{migration/schema}} change, security-sensitive,
  or ≳400 changed lines → plan critique (reviewer on the plan, before implementation)
  + review fan-out: 2–3 reviewer lenses (correctness / data-invariants / security),
  then a fresh refuter per candidate finding; only confirmed findings block the gate.

> **Token-level effort:** pin `effort: xhigh` in the architect and reviewer
> frontmatter; the other roles inherit the invoking session's effort. The tiers
> above scale review *breadth* (how many passes); frontmatter effort sets
> *depth per pass* — and floors the two highest-leverage roles against
> low-effort sessions. (No per-spawn effort override exists on the `Agent` tool.)

## Execution modes (default: subagents)

- **Subagent mode** (`/{{prefix}}-team` — works everywhere): the session is the lead;
  specialists are one-shot spawns. This is the default — the pipeline is mostly
  sequential (plan → implement → review), which is what subagents are for.
- **Live teams** (terminal, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): reserve for
  genuinely parallel-independent work — competing-hypothesis debugging, cross-layer
  work on disjoint file sets, broad research/review sweeps. Teams cost ~7x a normal
  session and add coordination overhead; official guidance recommends against them
  for sequential or same-file work. The reviewer stays a one-shot spawn even in
  teams mode — a standing reviewer teammate buys the 7x cost for a role that fires once.

> {{If a `<prefix>-qa` or similar skill already exists, note the test agent is
> `<prefix>-test`, distinct from that skill, and why.}}

## Spawning the team (v2.1.178+ — there is NO TeamCreate step)

The team auto-forms when the first teammate is spawned and auto-cleans on exit.
Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; live teammates are terminal-only.
In the desktop/web app use the **subagent** form via `/{{prefix}}-team` instead.

1. `Agent(subagent_type="{{prefix}}-<role>", name="<instance>")` for each specialist
   (omit `team_name` — ignored now). The `name` is how you address it via `SendMessage`.
2. `TaskCreate` per task with `addBlockedBy` deps so teammates self-claim and self-sequence.
3. Coordinate via `SendMessage` + the shared task list. Teammates inherit the lead's
   permission mode at spawn — pre-approve common ops first to avoid prompt friction.

## {{ProjectName}} guardrails every teammate must honor

- **Read first.** Read `AGENTS.md`{{ + design doc}} before touching a subsystem.
  {{schema-of-record}} is authoritative for {{shapes}}.
- **Worktree isolation.** Work only inside the current worktree dir; confirm
  `git rev-parse --show-toplevel`. {{isolation flag note, or "no special flag".}}
- **Tests:** `{{TEST_CMD}}` (full) / `{{TEST_CMD_FOCUSED}}` (focused). {{escape hatches}}.
- **Type/lint:** `{{TYPECHECK_CMD}}` must be green.
- **Migrations:** {{MIGRATION_WORKFLOW}}. {{additive-only / shared-schema caveats}}.
- **Hard invariants:** {{HARD_INVARIANTS — the CI-enforced rules}}.
- **Never bypass the pre-commit hook** — {{what it runs}}; no `--no-verify` without
  explicit per-commit authorization.
- **Deployment discipline.** {{DEPLOY_MODEL}}. Agents **never** {{the never-auto-run
  actions}}. Pushing / PRs / triggering builds are outward actions → surface for
  human go-ahead.
- **Branches/PRs:** ask for the {{LINEAR_PREFIX}} ID first; branch `{{branch fmt}}`;
  PR title `{{pr fmt}}`; target `{{base}}`; {{merge style}}.
- **Conventions:** {{parse-real-shapes / reuse-existing-patterns notes}}.

## Monitoring & recovery

- `git diff --stat HEAD` shows in-progress work (`git log` only shows commits → false
  "stalled" reads). See `/{{prefix}}-check-progress`.
- Recover an unresponsive instance via `/{{prefix}}-recover-agent`: confirm no active
  work → `SendMessage` shutdown_request → `TaskStop` → respawn with the **same** `name`.

## Done gate

The task is not done until: change implemented in the worktree; `{{TYPECHECK_CMD}}` +
`{{TEST_CMD_FOCUSED}}` green locally; {{migration generated/reviewed if schema changed}};
{{invariants}} respected; a fresh-context reviewer pass on the integrated diff with all
findings resolved or explicitly waived (waivers named in the delivery summary); and the
human has reviewed before any push/PR. None of the {{never-auto-run}} actions from an
agent context.
```
