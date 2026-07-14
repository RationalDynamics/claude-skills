# devo-skills

A shared marketplace of independently installable [Agent Skills](https://agentskills.io/) for
Claude and Codex. Five plugins use one provider-neutral skill implementation with native packaging
for both clients; the remaining plugins are still Claude-only.

## Claude + Codex skills

| Plugin | What it does |
|---|---|
| [`esoteric-elucidation`](plugins/esoteric-elucidation/skills/esoteric-elucidation/SKILL.md) | Orients an engineer in unfamiliar code, scopes the blast radius, and walks concrete data flows before implementation detail. |
| [`storm-research`](plugins/storm-research/skills/storm-research/SKILL.md) | Produces a multi-perspective, evidence-first long-form report with a deterministic citation audit. |
| [`costorm-session`](plugins/costorm-session/skills/costorm-session/SKILL.md) | Runs a steerable, resumable expert research roundtable that grows a shared mind map and cited report. |
| [`grill-me`](plugins/grill-me/skills/grill-me/SKILL.md) | Stress-tests a plan one decision at a time until its dependencies and assumptions are resolved. |
| [`tdd`](plugins/tdd/skills/tdd/SKILL.md) | Guides behavior-focused development through vertical red-green-refactor cycles. |

## Install with Claude

From an interactive Claude Code session:

```text
/plugin marketplace add RationalDynamics/claude-skills
/plugin install storm-research@devo-skills
/reload-plugins
```

Replace `storm-research` with any plugin above. The non-interactive CLI equivalents are:

```sh
claude plugin marketplace add RationalDynamics/claude-skills
claude plugin install storm-research@devo-skills
```

### Install everything

Want all of them? From a checkout, run the bundled script — it reads the plugin
list from the catalog (so it never drifts) and installs each one:

```sh
./install-all.sh
# or point it at a local checkout instead of GitHub:
# ./install-all.sh /path/to/claude-skills
```

If you'd rather not clone, add the marketplace once and loop over the names
(a plain shell one-liner, run outside the interactive `/plugin` prompt):

```sh
claude plugin marketplace add https://github.com/RationalDynamics/claude-skills
for p in breakpoint neuralize grill-me tdd esoteric-elucidation the-orchestrator \
         storm-research costorm-session camera-lens-travel-eval scaffold-agent-team \
         session-cost; do
  claude plugin install "$p@devo-skills"
done
```

> Skills load at session start, so start a fresh session after installing.

In Claude Code Desktop, use a local or SSH Code session. Enter `/plugin`, open **Marketplaces**, and
add `RationalDynamics/claude-skills` if needed. Then click **+ → Plugins → Add plugin**, choose
**Devo Skills**, and install the plugin. Claude's cloud/remote sessions do not load plugins. Plugin
skills become available after `/reload-plugins` or in a new session.

## Install with Codex

From a terminal:

```sh
codex plugin marketplace add RationalDynamics/claude-skills
codex plugin add storm-research@devo-skills
```

Replace `storm-research` with any cross-platform plugin above, then start a new Codex task so the
new skill is loaded.

In Codex Desktop, add the marketplace with the command above, restart the app, open **Plugins**,
select **Devo Skills**, and install the plugin. When developing from a local checkout, opening this
repository and restarting the app also exposes its repo marketplace at
`.agents/plugins/marketplace.json`.

## Invoke a skill

Marketplace-installed skills are namespaced because each plugin is independently installable.

| Plugin | Claude | Codex |
|---|---|---|
| `esoteric-elucidation` | `/esoteric-elucidation:esoteric-elucidation` | `$esoteric-elucidation:esoteric-elucidation` |
| `storm-research` | `/storm-research:storm-research` | `$storm-research:storm-research` |
| `costorm-session` | `/costorm-session:costorm-session` | `$costorm-session:costorm-session` |
| `grill-me` | `/grill-me:grill-me` | `$grill-me:grill-me` |
| `tdd` | `/tdd:tdd` | `$tdd:tdd` |

Codex users can also run `/skills` and select the installed skill. Both clients may invoke a skill
automatically when a request matches its description. Example prompts:

- “I'm new to this codebase—explain how billing events flow.”
- “Research solid-state batteries with STORM and produce a cited report.”
- “Start a steerable Co-STORM session about grid-scale storage.”
- “Grill me on this rollout plan.”
- “Implement this bug fix with a red-green-refactor loop.”

## Update installed plugins

Claude:

```text
/plugin marketplace update devo-skills
/reload-plugins
```

Codex:

```sh
codex plugin marketplace upgrade devo-skills
codex plugin add storm-research@devo-skills
```

Start a new task after a Codex reinstall. Avoid installing the same skill both directly and through
the marketplace; duplicate copies can appear as separate choices.

## Claude-only skills

These remain available from the Claude marketplace but are intentionally absent from the native
Codex marketplace until ported:

- [`breakpoint`](plugins/breakpoint/skills/breakpoint/SKILL.md) and [`neuralize`](plugins/neuralize/skills/neuralize/SKILL.md) — manual context checkpoints and selective context eviction.
- [`the-orchestrator`](plugins/the-orchestrator/skills/the-orchestrator/SKILL.md) — parallel task orchestration across worktrees.
- [`scaffold-agent-team`](plugins/scaffold-agent-team/skills/scaffold-agent-team/SKILL.md) — repo-specific agent-team scaffolding.
- [`camera-lens-travel-eval`](plugins/camera-lens-travel-eval/skills/camera-lens-travel-eval/SKILL.md) — an auditable worked-example evaluator.
- [`session-cost`](plugins/session-cost/skills/session-cost/SKILL.md) — Claude session cost and usage reporting.

## Develop locally

Load one Claude plugin directly without installing it:

```sh
claude --plugin-dir ./plugins/tdd
```

Test the native Codex marketplace from this checkout:

```sh
codex plugin marketplace add "$PWD"
codex plugin add tdd@devo-skills
```

After changing a marketplace-installed plugin, reinstall it and open a fresh task/session before
testing. Use only one loading mechanism per skill.

## Add or port a skill

Read [`AGENTS.md`](AGENTS.md) before editing packaging or shared skill instructions. A
cross-platform plugin must have:

- one provider-neutral `skills/<name>/SKILL.md` with only `name` and `description` frontmatter;
- `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` with synchronized common metadata;
- `skills/<name>/agents/openai.yaml` for Codex UI and invocation policy;
- entries in the Claude catalog and, once ported, the Codex catalog;
- self-contained references/scripts and passing repository validation.

Run the checks before opening a PR:

```sh
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_cross_platform.py
claude plugin validate --strict .
```

## Layout

```text
.claude-plugin/marketplace.json       # complete Claude catalog
.agents/plugins/marketplace.json      # native Codex catalog: ported plugins only
plugins/<name>/.claude-plugin/plugin.json
plugins/<name>/.codex-plugin/plugin.json
plugins/<name>/skills/<name>/SKILL.md
plugins/<name>/skills/<name>/agents/openai.yaml
plugins/<name>/skills/<name>/references/
plugins/<name>/skills/<name>/scripts/
```
