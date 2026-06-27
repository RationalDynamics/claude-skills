# Extraction checklist

What to pull from the target repo before generating anything. Each row becomes a
`{{PLACEHOLDER}}` in the templates. Read `AGENTS.md`/`CLAUDE.md`, `README.md`, the
dev wrapper (Makefile / `command.sh` / `scripts/`), the package manifest, CI config,
Dockerfile, and the `docs/`/`terraform/` layout. Quote rules verbatim where they're rules.

| Placeholder | What to find | Where to look |
|---|---|---|
| `{{repo}}` / `{{ProjectName}}` / `{{prefix}}` | repo name + a short slug for agent names | repo root, package manifest |
| `{{stack}}` | languages, frameworks, runtime, DB, key libs | manifest, Dockerfile, AGENTS.md |
| subsystem → role map | the natural ownership boundaries (API, data layer, workers/pipeline, infra, UI) | source-tree layout, AGENTS.md "repo layout" |
| `{{TEST_CMD}}` / `{{TEST_CMD_FOCUSED}}` | exact full-suite and focused-run commands; what infra a run needs | dev wrapper, README, CI, pyproject/package.json scripts |
| `{{TYPECHECK_CMD}}` | type-check / lint gate command | dev wrapper, CI, pre-commit hook |
| `{{MIGRATION_WORKFLOW}}` + caveats | how schema changes are authored & applied; additive-only? shared schema? | migrations dir + its README, AGENTS.md |
| `{{SCHEMA_OF_RECORD}}` | the file/endpoint authoritative for data shapes (ORM models, OpenAPI, proto) | models module, `/openapi.json`, schema endpoint |
| `{{DEPLOY_MODEL}}` + **never-auto-run actions** | branch model; what merging to main does; how prod is promoted; which deploy/infra commands an agent must never run | README "deploy", cloudbuild/CI, publish/deploy scripts, AGENTS.md |
| `{{HARD_INVARIANTS}}` | CI-enforced rules (egress/import boundaries, constraints) + the pre-commit hook contents + bypass policy | invariant tests, `.githooks/`, AGENTS.md |
| `{{LINEAR_PREFIX}}` + branch/PR format | ticket prefix; branch naming; PR title format; merge style | git log, AGENTS.md, CONTRIBUTING |
| isolation rules | worktree discipline, compose-isolation flags, shared DB ports | AGENTS.md, local-dev doc |
| existing collisions | any existing `<prefix>-*` skill/agent the team names must not clash with | `.claude/skills/`, `.claude/agents/`, `~/.claude/` |

## Roster decision rules

- Always: `lead`, `architect`, `backend`, `test`.
- `devops`: include **only** if the repo has infra/Terraform/CI worth owning. Otherwise drop it.
- `frontend`: add if the repo ships a UI surface distinct from the backend.
- Rename `backend`→`engineer`/`core` for non-web stacks (CLI, library, data pipeline).
- Models: orchestration/impl/test = sonnet; deep-reasoning (architect, devops) = opus. State them; let the user override.

## Naming collision rule

If the repo (or `~/.claude`) already defines a skill or agent that would share a name
with a team role — e.g. an existing `<prefix>-qa` *skill* vs a would-be `<prefix>-qa`
*agent* — pick a non-colliding role name (e.g. `<prefix>-test`) and note the distinction
in the agent + protocol. (This exact case happened with rd-dis's `dis-qa` skill.)
