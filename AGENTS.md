# Repository instructions

## Scope

This repository distributes independently installable Agent Skills. Treat shared skill content as
provider-neutral and put client-specific behavior in packaging metadata.

The current cross-platform plugins are exactly:

- `esoteric-elucidation`
- `storm-research`
- `costorm-session`
- `grill-me`
- `tdd`

Do not add another plugin to `.agents/plugins/marketplace.json` until it has been deliberately
ported and passes the rules below. The Claude catalog may continue to contain Claude-only plugins.

## Shared skill contract

- Put the reusable workflow in `plugins/<name>/skills/<name>/SKILL.md`.
- Use only `name` and `description` in `SKILL.md` frontmatter. Keep names lower-case kebab-case,
  under 64 characters, and identical to the skill directory.
- Write descriptions that say what the skill does and when it should trigger. Keep them under 1,024
  characters and avoid literal angle brackets.
- Write instructions in imperative, provider-neutral language. Do not name client-specific tools,
  commands, invocation syntax, or brands in shared `SKILL.md` and `references/` content.
- Describe required capabilities generically, such as “live web search,” “page fetching,” “native
  subagents,” or “the current client's file-delivery capability.” Respect the host's concurrency
  limits instead of assuming a particular parallel call shape.
- Resolve bundled scripts and assets relative to the skill directory, preferably by absolute path
  at runtime. Never assume the user's working directory is the installed plugin cache.
- Keep every plugin self-contained. Do not require files from a sibling plugin; copy the minimal
  reusable policy locally or declare a supported dependency in both packaging systems.
- Keep detailed schemas and examples in directly linked `references/` files. Avoid deep reference
  chains and unnecessary files inside skill directories.

## Packaging contract

- Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` in every cross-platform plugin.
- Synchronize `name`, `version`, `description`, `author`, and `skills` across both manifests. Bump
  the semantic version in both whenever installed behavior or packaging changes.
- Keep Codex presentation metadata under `.codex-plugin/plugin.json.interface` and skill metadata
  under `skills/<name>/agents/openai.yaml`.
- In `agents/openai.yaml`, quote string values, keep `short_description` between 25 and 64
  characters, mention `$<skill-name>` in `default_prompt`, and set
  `policy.allow_implicit_invocation` deliberately.
- Register all plugins in `.claude-plugin/marketplace.json`. Register only fully ported plugins in
  `.agents/plugins/marketplace.json`, with a local `./plugins/<name>` source, availability and
  authentication policy, and category.
- Keep invocation examples out of shared skills. User docs should show Claude `/plugin:skill` and
  Codex `$plugin:skill` or `/skills` explicitly.

## Required workflow for a new cross-platform plugin

1. Create or port the provider-neutral skill and its local resources.
2. Add synchronized Claude and Codex manifests.
3. Generate `agents/openai.yaml` with the skill-creator tooling, then set the invocation policy.
4. Register the plugin in both marketplace catalogs.
5. Update `README.md` and the team Notion guide with installation and invocation examples.
6. Run all validation below and perform a fresh-session smoke test in both clients.

## Validation

Run from the repository root:

```sh
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate_cross_platform.py
claude plugin validate --strict .
```

For each changed cross-platform skill, also run:

```sh
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" plugins/<name>/skills/<name>
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" plugins/<name>
```

For Codex packaging changes, use an isolated `CODEX_HOME`, add this repository as a local
marketplace, and install every cross-platform plugin. Start a new task before testing invocation.
