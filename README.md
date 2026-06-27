# claude-skills

A small collection of [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
for Claude Code / Cowork. Each skill is a self-contained folder with a `SKILL.md`
(YAML frontmatter + instructions) and optional `references/` (progressively-loaded
detail) and `scripts/` (deterministic helpers).

## Skills

### [`storm-research`](storm-research/SKILL.md)
One-shot, perspective-driven long-form research that reimplements Stanford OVAL's
[STORM](https://github.com/stanford-oval/storm) method: discover several expert
perspectives → run a simulated research conversation per perspective → build an
evidence-grounded outline → draft a Wikipedia-style article section by section with
inline citations → polish → a deterministic citation audit
([`audit_citations.py`](storm-research/scripts/audit_citations.py)). It fans out
parallel research subagents and writes staged artifacts (brief, perspectives,
evidence, outline, report, sources, audit). A native alternative to "deep research"
for broad, balanced, sectioned topics.

### [`costorm-session`](costorm-session/SKILL.md)
Interactive, human-in-the-loop reimplementation of Co-STORM: a steerable, turn-based
discourse among LLM expert agents and a moderator while you observe and steer, growing
a shared dynamic mind map turn by turn, then synthesizing a cited report from it. The
session state is model-managed JSON that persists to disk, so a session can be resumed.

### [`camera-lens-travel-eval`](camera-lens-travel-eval/SKILL.md)
A worked-example eval skill. It grades a candidate model answer to a specific
travel-lens question (Sony a7R VI/V vs Leica M10 kits) using a 100-point rubric, a
gold-fact baseline, line-grounded evidence selection, and score caps for critical
errors. Useful as a template for building rigorous, auditable evals.

### [`scaffold-agent-team`](scaffold-agent-team/SKILL.md)
Stands up a **repo-coupled multi-agent team** for a target repository: it reads the
repo's conventions (stack, test/type gates, migration workflow, deploy discipline,
hard invariants) and emits customized, project-local Claude Code agents
(lead/architect/backend/test/devops, adapted per repo), slash commands, and a
coordination protocol — then adversarially verifies the generated claims against the
repo. The generalized recipe behind the scry-team (scry-api) and dis-team (rd-dis).
Unlike the other skills here, its output is version-controlled config that lives **in
the target repo**, not a portable artifact.

## Install

Claude Code discovers skills from `~/.claude/skills/<name>/` (personal, available in
every project) or `<project>/.claude/skills/<name>/` (project-local). Symlink (keeps a
single editable copy) or copy the folders:

```sh
# personal install
ln -s "$PWD/storm-research"          ~/.claude/skills/storm-research
ln -s "$PWD/costorm-session"         ~/.claude/skills/costorm-session
ln -s "$PWD/camera-lens-travel-eval" ~/.claude/skills/camera-lens-travel-eval
ln -s "$PWD/scaffold-agent-team"     ~/.claude/skills/scaffold-agent-team
```

## Layout

```
<skill>/
  SKILL.md          # frontmatter (name, description) + instructions
  references/*.md   # detail loaded on demand
  scripts/*         # optional deterministic helpers
```
