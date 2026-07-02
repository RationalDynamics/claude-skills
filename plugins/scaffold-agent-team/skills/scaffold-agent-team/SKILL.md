---
name: scaffold-agent-team
description: >-
  Scaffold a per-repo multi-agent "team" (lead + architect + backend + test +
  reviewer + devops, adapted per repo) by reading the target repo's conventions and emitting
  customized, project-local Claude Code agents, slash commands, and a coordination
  protocol — the same pattern as the scry-team (scry-api) and dis-team (rd-dis).
  Use when the user wants to "set up an agent team", "create a dev team for this
  repo", "clone the scry-team / dis-team pattern", "make a multi-agent team for
  <repo>", or stand up architect/backend/qa/devops subagents tuned to a codebase.
  Produces version-controlled, repo-coupled config — not a portable skill. Trigger
  on "scaffold an agent team", "give this repo a team like scry/dis", "spin up a
  multi-agent team here".
---

# scaffold-agent-team

Stand up a **repo-coupled multi-agent team** — a small roster of specialist
subagents (architect, backend, test, devops, …) plus the slash commands and the
coordination protocol that drive them — customized to one repository's actual
stack, commands, gates, and deploy discipline.

This is the generalized recipe behind two existing instances:
- **scry-team** — scry-api (Django/DRF/Celery/Postgres/LangGraph, GCP Cloud Run)
- **dis-team** — rd-dis (FastAPI/Pydantic/SQLAlchemy/Alembic, Cloud Tasks, Cloud Run)

See `references/examples.md` for both, filled in, plus the customization mapping.

## What this produces (and where it lives)

A team is **coupled to one repo** — it hardcodes that repo's test command, file
paths, invariants, and deploy model. So it belongs **in that repo**, version-
controlled, not in a central/portable skills library. Default output (project-local):

```
<repo>/docs/agent-team.md                       # canonical protocol + roster + done gate
<repo>/.claude/agents/<prefix>-lead.md           # orchestrator (no code)
<repo>/.claude/agents/<prefix>-architect.md      # plan/design (no app code)
<repo>/.claude/agents/<prefix>-backend.md        # implementation
<repo>/.claude/agents/<prefix>-test.md           # tests + type/lint gates
<repo>/.claude/agents/<prefix>-reviewer.md       # fresh-context diff review (read-only)
<repo>/.claude/agents/<prefix>-devops.md         # infra/CI/deploy (only if infra exists)
<repo>/.claude/commands/<prefix>-team.md          # /<prefix>-team orchestrator
<repo>/.claude/commands/<prefix>-team-status.md
<repo>/.claude/commands/<prefix>-project-status.md
<repo>/.claude/commands/<prefix>-check-progress.md
<repo>/.claude/commands/<prefix>-recover-agent.md
<repo>/AGENTS.md (or CLAUDE.md)                   # add an "Agent team (opt-in)" pointer
```

**Project-local vs global:** project-local is the default and the recommendation —
it ships with the repo, is reviewed in PRs, and stays in sync with the code it
drives. Mirror to `~/.claude/{agents,commands}/` only if the user wants the team
available from any cwd (rarely needed for a repo-specific team — you're in the repo
when you use it). The legacy scry-team lives global-only/uncommitted; don't repeat that.

## Procedure

**1 — Intake.** Identify the target repo (default: the cwd's repo root,
`git rev-parse --show-toplevel`; confirm if ambiguous). Pick a short **prefix** —
a repo slug (`dis`, `scry`). Ask the user only what you can't infer: install scope
(project-local default), and whether to commit/PR at the end. If the repo already
has a team (`<prefix>-*` agents), this is an update, not a fresh scaffold.

**2 — Read the repo's conventions (the extraction step — do this thoroughly).**
Read `AGENTS.md` and/or `CLAUDE.md`, `README.md`, the dev/Makefile/`command.sh`
wrapper, `pyproject.toml`/`package.json`/`go.mod`, CI config, Dockerfile, and the
`docs/`/`terraform/` layout. Extract — verbatim where it's a rule — the
`references/extraction-checklist.md` items:
  - **Stack & subsystems** — languages, frameworks, runtime, DB; the natural
    ownership boundaries (API, data layer, workers/pipeline, infra, etc.).
  - **Quality gates** — exact test command(s), type-check/lint command, the
    full-suite vs focused-run forms, any env/infra a test run needs.
  - **Migrations / schema** — how schema changes are made and applied; where the
    schema-of-record lives; the endpoint/file that is authoritative for shapes.
  - **Deploy & promotion** — branch model, what merging to main does, how prod is
    promoted, and which deploy/infra actions an agent must **never** auto-run.
  - **Hard invariants** — repo-enforced rules (egress boundaries, import hygiene,
    constraints) that CI fails on; the pre-commit hook and its bypass policy.
  - **Project mgmt** — Linear/ticket prefix, branch naming, PR title format, merge style.
  - **Worktree/isolation** rules, if any.

**3 — Choose the roster (adaptive).** Base 6: `lead` (sonnet, orchestrator, no
code), `architect` (fable, plan/design, no app code), `backend` (sonnet,
implementation), `test` (sonnet, tests + gates), `reviewer` (fable, fresh-context
diff review, read-only, spawned per task), `devops` (sonnet, infra/CI/deploy).
Adapt: add `frontend` if the repo ships a UI; **drop `devops`** if there's no
infra/Terraform/CI to own; rename `backend`→`engineer` for non-web stacks. Keep
`reviewer` — it's the completeness gate, and as a one-shot end-of-pipeline spawn its
cost is bounded. Default models: orchestration/impl/test/devops = sonnet,
deep-reasoning (architect, reviewer) = fable, with `effort: xhigh` pinned in the
architect + reviewer frontmatter (other roles inherit the invoking session's
effort) — state them and let the user override.

**4 — Generate the protocol doc** (`docs/agent-team.md`) from
`references/protocol-template.md`, filling every `{{PLACEHOLDER}}` from step 2.
This is the canonical file the agents and commands point at.

**5 — Generate the agents** from `references/role-templates.md` (one per chosen
role). Each agent: reads the protocol + AGENTS.md first; owns its slice; honors the
repo's gates and the no-auto-deploy discipline; reports to the lead. The architect
and lead write no code; the reviewer never edits anything.

**6 — Generate the commands** from `references/command-templates.md`
(`<prefix>-team` orchestrator + the four monitoring commands).

**7 — Add the pointer** — an "Agent team (opt-in)" section in `AGENTS.md`/`CLAUDE.md`
listing the roster, the commands, and that it honors the repo's gates.

**8 — Adversarially verify (do not skip).** Every generated file makes factual
claims about the repo; verify them. Spawn (or run) three independent checks — see
`references/verification.md`:
  - **facts** — every command, path, gate, invariant, and deploy claim checked
    against the actual repo (does the test command exist? does that file path
    resolve? is the schema-of-record where you said?).
  - **leftovers** — no un-customized residue from the source pattern (no Django in
    a FastAPI repo, no `./command.sh test` if the repo uses `make test`, etc.).
  - **consistency** — agent `name:`s, instance names, models, and cross-file
    references all agree; commands point at real agent files; no name collision
    with an **existing** skill/agent (e.g. a `<prefix>-qa` skill already present →
    name the test agent `<prefix>-test`).
  Fix every medium+ finding, then re-sweep.

**9 — Deliver.** Summarize the roster + files. Pushing/PR is an outward action:
do it only if the user asked, on a branch named per the repo's convention, PR title
in the repo's format. The team is opt-in — nothing runs until `/<prefix>-team` is
invoked.

## Customization checklist (what MUST be repo-specific)

The whole value is that the team is *grounded in this repo*. Before delivering,
confirm none of these are generic or copied from another instance:
`{{TEST_CMD}}` · `{{TYPECHECK_CMD}}` · `{{MIGRATION_WORKFLOW}}` ·
`{{SCHEMA_OF_RECORD}}` · `{{DEPLOY_MODEL}}` + the never-auto-run actions ·
`{{HARD_INVARIANTS}}` · `{{LINEAR_PREFIX}}`/branch/PR format · the subsystem→role
ownership map · the source-tree paths each agent cites.

## Guardrails

- **Verify before you ship.** A team that cites a wrong path or a non-existent
  command is worse than none — it confidently misdirects every subagent. Step 8 is
  mandatory; the dis-team scaffold caught a real wrong-schema-path bug this way.
- **No leftovers.** Scrub every trace of the source pattern's stack. If you cloned
  from scry-team, there must be zero Django/DRF/Celery/`/api/schema/` unless the
  target genuinely uses them.
- **Repo-coupled → lives in the repo.** Do not put a generated team in a central
  skills repo; project-local is the home. (This skill is the only portable piece.)
- **Respect outward-action discipline.** Encode the repo's deploy rules into the
  devops/lead agents (never auto-`apply`/promote); and don't auto-push/PR the
  scaffold itself unless asked.
- **Don't invent gates.** Every gate/command in the output must be one you verified
  exists in the target repo.

## Reference files

`references/protocol-template.md` · `references/role-templates.md` ·
`references/command-templates.md` · `references/extraction-checklist.md` ·
`references/verification.md` · `references/examples.md` (scry-team + dis-team, filled in)
