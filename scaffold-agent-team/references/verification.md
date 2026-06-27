# Verification (step 8) — mandatory before delivery

A generated team makes dozens of factual claims about the repo (commands, paths,
gates, invariants, deploy rules). If any are wrong, the team confidently misdirects
every subagent that trusts them. So verify the output against the actual repo before
shipping. (Scaffolding the dis-team this way caught a real wrong-schema-path bug.)

## How to run it

Best as a parallel fan-out — spawn three independent `Agent` checks, one per lens,
each given the list of generated files + the repo root, each returning structured
findings (`{file, claim, issue, evidence, severity, suggested_fix}`). For a small
team you can also do the three passes inline. Fix every **medium+** finding, then
re-sweep for leftover tokens.

## The three lenses

**1 — Facts.** Every Dis-/repo-specific claim checked against the real repo:
- Does each command exist and behave as described? (`{{TEST_CMD}}`, `{{TYPECHECK_CMD}}`,
  focused-run form, escape hatches) — read the dev wrapper / scripts.
- Does every cited **file path** resolve? (source dirs, the schema-of-record, docs,
  infra modules, design doc). `ls`/`find` them.
- Is the migration workflow, deploy model, and each "never-auto-run" action accurate?
- Are the hard invariants real (is there actually a test/hook enforcing them)?

**2 — Leftovers.** No un-customized residue from the source pattern. If cloned from
scry-team, scan for and kill anything that doesn't apply: the wrong framework
(Django/DRF/Celery in a non-Django repo), the wrong test command (`./command.sh test`
where the repo uses `make test`), a schema endpoint that doesn't exist here
(`/api/schema/`), stage→prod promotion the repo doesn't have, stray mentions of the
source repo's name where the target's belongs. Legitimate cross-repo references (a
design doc that genuinely lives in a sibling repo) are fine — don't flag those.

**3 — Consistency.** Cross-file coherence and resolvability:
- Agent `name:` values are spelled identically everywhere (frontmatter, protocol
  roster table, lead's composition list, every command).
- Instance names + model tiers agree across the protocol, agent frontmatter, and
  `<prefix>-team-status`.
- Commands reference real agent file paths; the AGENTS.md pointer's links/command
  names match the files actually created.
- **No name collision** with an existing skill/agent in the repo or `~/.claude/`.
- Frontmatter well-formed (agents: `name`+`description`+`model`; commands: `description`).

## After fixing

Re-grep the generated files for: the source pattern's stack keywords (should be 0
unless the target uses them), any remaining `{{PLACEHOLDER}}` (should be 0), and any
broken path token you replaced. A clean sweep + a green re-read = done.
