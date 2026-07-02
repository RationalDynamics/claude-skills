# Worked examples — two filled-in instances

Two real teams built from this pattern. Use them to see how the `{{PLACEHOLDERS}}`
resolve for a real repo, and how the roster/gates/deploy-rules differ by stack.

## Side-by-side mapping

| Placeholder | **scry-team** (scry-api) | **dis-team** (rd-dis) |
|---|---|---|
| `{{prefix}}` | `scry` | `dis` |
| `{{stack}}` | Django 6 / DRF + drf-spectacular, Celery + Redis, Postgres 16, LangGraph over OpenAI+Anthropic | FastAPI + Pydantic v2, SQLAlchemy 2.0 / asyncpg, Alembic, Cloud Tasks + Cloud Scheduler |
| deploy target | GCP Cloud Run | GCP Cloud Run |
| roster | lead, architect, backend, qa, reviewer (one-shot), devops (no frontend — separate repo) | lead, architect, backend, **test**, reviewer (one-shot), devops |
| `{{TEST_CMD}}` | `./command.sh test` (full) / `./command.sh test tests/path.py -q` (focused) — never `./command.sh pytest -q` | `./command.sh test` (full, real Postgres + live EDGAR) / `./command.sh test tests/path.py -q` (focused) |
| `{{TYPECHECK_CMD}}` | (part of the suite) | `./command.sh check` (mypy strict) |
| escape hatches | `SCRY_COMPOSE_ISOLATED=1` for `manage` in a worktree | `./command.sh pytest-host` (no infra), `DIS_SKIP_INTERNET=1` (skip live SEC); **no** isolation flag |
| `{{MIGRATION_WORKFLOW}}` | `manage makemigrations <app>` → `migrate` → `showmigrations` → `render_datamodel_diagrams`; additive, never renumber | Alembic autogenerate in `packages/rd-datalake/.../migrations/` → review → `rd-dis migrate`; additive; **shared schema** (scry-api consumes it next) |
| `{{SCHEMA_OF_RECORD}}` | `GET /api/schema/` + the real persisted `raw_output` shape | `/openapi.json` + `packages/rd-datalake/src/rd_datalake/models.py` |
| `{{DEPLOY_MODEL}}` | promotion `main`→`stage`→`prod`; PRs target `main`; no stage/prod unless user says "hotfix" | `main` auto-deploys prototype; `./publish.sh` promotes main→prod; **no stage tier** |
| never-auto-run | push/deploy/trigger `stage`/`prod` | `terraform apply` (user applies infra), `./publish.sh` (prod promotion) |
| `{{HARD_INVARIANTS}}` | exactly-one-of CheckConstraints, PROTECT/thesis invariants, org-scoping, reuse `manager_*_id` keys | SEC egress only in `sources/` (`test_egress_invariant.py`), no `api/`↔`pipeline/` imports, function-scope heavy imports, `Settings` frozen + `DIS_LOCAL_MODE` tripwire |
| pre-commit hook | full pytest suite; never `--no-verify` | `./command.sh check` + `./command.sh test` + `terraform fmt -check`; never `--no-verify` without per-commit auth |
| `{{LINEAR_PREFIX}}` | per scry-api convention | `DEM` (Demo Team); branch `<author>/dem-NNN-desc`; PR `[DEM-NNN] Desc`; squash |
| design doc | the relevant `docs/<area>.md` | `scry-api/docs/dis_lld.md` (lives in a sibling repo — a legit cross-repo ref) |
| install location | global `~/.claude/` (legacy — uncommitted; **don't repeat this**) | **project-local**, committed to rd-dis (recommended) |
| naming note | — | test agent is `dis-test`, not `dis-qa` — a `dis-qa` *skill* already exists for post-deploy observational QA |

## Key lessons these encode

- **Project-local beats global.** scry-team lives only in `~/.claude` (unversioned,
  invisible to teammates). dis-team ships in the repo. Default new teams to project-local.
- **Deploy discipline is the highest-stakes customization.** scry's three-tier
  promotion and dis's "never `terraform apply`/`publish.sh`" are different rules for
  different repos — get this exactly right; it's the difference between a safe and a
  dangerous team.
- **The schema-of-record differs by stack** (DRF schema endpoint vs FastAPI OpenAPI +
  the ORM module). The architect/test agents must point at the real one.
- **Watch for collisions** with existing skills/agents (the `dis-qa` case).
- **Verify the output** — the dis-team scaffold initially cited a non-existent
  `src/rd_dis/registry/models.py`; step-8 verification caught and fixed it.

## Reading the live instances

- scry-team: `~/.claude/agents/scry-*.md`, `~/.claude/commands/{scry-team,team-status,project-status,check-agent-progress,recover-stuck-agent}.md`, `~/.claude/rules/scry-team-structure.md`.
- dis-team: `rd-dis/.claude/agents/dis-*.md`, `rd-dis/.claude/commands/dis-*.md`, `rd-dis/docs/agent-team.md`, and the "Agent team (opt-in)" section of `rd-dis/AGENTS.md`.
