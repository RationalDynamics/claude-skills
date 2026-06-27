# devo-skills

A shared **plugin marketplace** of [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
for Claude Code / Cowork. Each skill is packaged as its own **peer plugin**, so you
install only the ones you want — and the team can add their own by dropping a folder
in `plugins/` and one entry in the catalog.

## Use it

Add the marketplace once, then install the plugins you want:

```sh
# point at this checkout (local), or a git URL once it's pushed
/plugin marketplace add /Users/chris/devo/skills
# /plugin marketplace add https://github.com/RationalDynamics/claude-skills

# install à la carte — each skill is independent
/plugin install storm-research@devo-skills      # à la carte
/plugin install breakpoint@devo-skills
```

Pull in new/updated skills later with `/plugin marketplace update devo-skills`, then
`/plugin install <name>@devo-skills`. (The `/plugin` commands run from an interactive
`claude` terminal session.)

> Skills load at session start, so start a fresh session after installing.

## Skills

**Research**
- [`storm-research`](plugins/storm-research/skills/storm-research/SKILL.md) — one-shot, perspective-driven long-form research (Stanford STORM): discover perspectives → simulated research conversations → evidence-grounded outline → sectioned cited article → deterministic citation audit.
- [`costorm-session`](plugins/costorm-session/skills/costorm-session/SKILL.md) — interactive, human-in-the-loop Co-STORM: a steerable turn-based discourse among LLM experts + a moderator over web sources, growing a shared mind map, then a cited report. Resumable.

**Context management** *(slash-invoked only — `disable-model-invocation`)*
- [`breakpoint`](plugins/breakpoint/skills/breakpoint/SKILL.md) — insert `/breakpoint` markers that divide a session into logical blocks.
- [`neuralize`](plugins/neuralize/skills/neuralize/SKILL.md) — `/neuralize` selectively evicts irrelevant blocks and reloads only what matters; the surgical alternative to clearing a whole session. Pairs with `breakpoint`.

**Development workflow**
- [`tdd`](plugins/tdd/skills/tdd/SKILL.md) — red-green-refactor TDD loop, with references on deep modules, interface design, mocking, and refactoring.
- [`the-orchestrator`](plugins/the-orchestrator/skills/the-orchestrator/SKILL.md) — decompose a design doc into a parallelizable DAG of tasks and run them across git worktrees with an interactive visual workflow.
- [`esoteric-elucidation`](plugins/esoteric-elucidation/skills/esoteric-elucidation/SKILL.md) — explain unfamiliar code/systems in plain English, scoping blast radius and walking data flows before implementation detail.
- [`scaffold-agent-team`](plugins/scaffold-agent-team/skills/scaffold-agent-team/SKILL.md) — scaffold a repo-coupled multi-agent team (lead/architect/backend/qa/devops) tuned to a target repo's conventions. The recipe behind the scry-team and dis-team.
- [`grill-me`](plugins/grill-me/skills/grill-me/SKILL.md) — interview the user relentlessly about a plan or design, resolving each branch of the decision tree until shared understanding.

**Evals**
- [`camera-lens-travel-eval`](plugins/camera-lens-travel-eval/skills/camera-lens-travel-eval/SKILL.md) — worked-example eval: grades a candidate answer with a 100-point rubric, gold-fact baseline, line-grounded evidence, and critical-error caps. A template for rigorous, auditable evals.

## Add your own skill

1. **Create the skill** at `plugins/<name>/skills/<name>/SKILL.md` (plus optional
   `references/`, `scripts/`, `assets/`). The `SKILL.md` frontmatter needs at least
   `name` and `description`.
2. **Add a plugin manifest** at `plugins/<name>/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "<name>",
     "description": "One-line catalog summary shown in /plugin.",
     "version": "0.1.0",
     "author": { "name": "you", "email": "you@example.com" }
   }
   ```
3. **Register it** in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
   by appending an entry to `plugins[]`:
   ```json
   { "name": "<name>", "source": "./plugins/<name>", "description": "…", "category": "…" }
   ```
4. **Open a PR.** After merge, teammates run `/plugin marketplace update devo-skills`
   then `/plugin install <name>@devo-skills`.

## Layout

```
.claude-plugin/
  marketplace.json          # the catalog: lists every plugin
plugins/<name>/
  .claude-plugin/
    plugin.json             # plugin manifest (name, description, version, author)
  skills/<name>/
    SKILL.md                # frontmatter (name, description) + instructions
    references/*.md         # detail loaded on demand
    scripts/*               # optional deterministic helpers
```

> **Local dev shortcut:** instead of installing via the marketplace you can symlink a
> single skill into `~/.claude/skills/`, e.g.
> `ln -s "$PWD/plugins/tdd/skills/tdd" ~/.claude/skills/tdd`. Use one mechanism or the
> other per skill — don't both symlink *and* install the same skill, or it loads twice.
