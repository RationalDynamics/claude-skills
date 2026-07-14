#!/usr/bin/env python3
"""Validate the repository's Claude/Codex cross-platform skill contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


CROSS_PLATFORM_PLUGINS = (
    "esoteric-elucidation",
    "storm-research",
    "costorm-session",
    "grill-me",
    "tdd",
)

CATEGORIES = {
    "esoteric-elucidation": "Development",
    "storm-research": "Research",
    "costorm-session": "Research",
    "grill-me": "Productivity",
    "tdd": "Development",
}

COMMON_MANIFEST_FIELDS = ("name", "version", "description", "author", "skills")
REQUIRED_CODEX_INTERFACE_FIELDS = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "defaultPrompt",
)
FORBIDDEN_SHARED_TOKENS = (
    "Claude",
    "Codex",
    "ToolSearch",
    "WebSearch",
    "WebFetch",
    "SendUserFile",
    "`Agent`",
    "Agent calls",
)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to this script's parent repository)",
    )
    return parser.parse_args()


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON at {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"expected a JSON object at {path}")
        return {}
    return payload


def load_yaml(path: Path, errors: list[str]) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"invalid YAML at {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"expected a YAML mapping at {path}")
        return {}
    return payload


def load_skill_frontmatter(path: Path, errors: list[str]) -> tuple[dict, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}, ""
    if not text.startswith("---\n"):
        errors.append(f"SKILL.md must begin with YAML frontmatter: {path}")
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        errors.append(f"SKILL.md frontmatter is not closed: {path}")
        return {}, text
    try:
        frontmatter = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        errors.append(f"invalid SKILL.md frontmatter at {path}: {exc}")
        return {}, text
    if not isinstance(frontmatter, dict):
        errors.append(f"SKILL.md frontmatter must be a mapping: {path}")
        return {}, text
    return frontmatter, text


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def validate_markdown_links(plugin_root: Path, errors: list[str]) -> None:
    for markdown in plugin_root.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().strip("<>")
            split = urlsplit(target)
            if split.scheme or target.startswith(("#", "mailto:")):
                continue
            relative = unquote(split.path)
            if not relative:
                continue
            resolved = markdown.parent / relative
            if not inside(resolved, plugin_root):
                errors.append(f"relative link escapes plugin root: {markdown} -> {target}")
            elif not resolved.exists():
                errors.append(f"relative link target is missing: {markdown} -> {target}")


def validate_plugin_files(plugin_root: Path, errors: list[str]) -> None:
    for path in plugin_root.rglob("*"):
        if path.is_symlink() and not inside(path, plugin_root):
            errors.append(f"symlink escapes plugin root: {path}")
    validate_markdown_links(plugin_root, errors)


def validate_marketplaces(repo: Path, errors: list[str]) -> None:
    codex_path = repo / ".agents" / "plugins" / "marketplace.json"
    claude_path = repo / ".claude-plugin" / "marketplace.json"
    codex = load_json(codex_path, errors)
    claude = load_json(claude_path, errors)

    if codex.get("name") != "devo-skills":
        errors.append("Codex marketplace name must be `devo-skills`")
    if (codex.get("interface") or {}).get("displayName") != "Devo Skills":
        errors.append("Codex marketplace displayName must be `Devo Skills`")

    entries = codex.get("plugins")
    if not isinstance(entries, list):
        errors.append("Codex marketplace `plugins` must be an array")
        entries = []
    names = [entry.get("name") for entry in entries if isinstance(entry, dict)]
    if names != list(CROSS_PLATFORM_PLUGINS):
        errors.append(
            "Codex marketplace must contain exactly the approved plugins in canonical order: "
            + ", ".join(CROSS_PLATFORM_PLUGINS)
        )
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Codex marketplace entries must be objects")
            continue
        name = entry.get("name")
        if name not in CROSS_PLATFORM_PLUGINS:
            continue
        expected_source = {"source": "local", "path": f"./plugins/{name}"}
        if entry.get("source") != expected_source:
            errors.append(f"Codex marketplace source is wrong for {name}")
        if entry.get("policy") != {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        }:
            errors.append(f"Codex marketplace policy is wrong for {name}")
        if entry.get("category") != CATEGORIES[name]:
            errors.append(f"Codex marketplace category is wrong for {name}")

    claude_entries = claude.get("plugins")
    if not isinstance(claude_entries, list):
        errors.append("Claude marketplace `plugins` must be an array")
        claude_entries = []
    claude_by_name = {
        entry.get("name"): entry for entry in claude_entries if isinstance(entry, dict)
    }
    for name in CROSS_PLATFORM_PLUGINS:
        entry = claude_by_name.get(name)
        if entry is None:
            errors.append(f"Claude marketplace is missing {name}")
        elif entry.get("source") != f"./plugins/{name}":
            errors.append(f"Claude marketplace source is wrong for {name}")


def validate_one_plugin(repo: Path, name: str, errors: list[str]) -> None:
    plugin_root = repo / "plugins" / name
    claude_path = plugin_root / ".claude-plugin" / "plugin.json"
    codex_path = plugin_root / ".codex-plugin" / "plugin.json"
    claude = load_json(claude_path, errors)
    codex = load_json(codex_path, errors)

    for field in COMMON_MANIFEST_FIELDS:
        if claude.get(field) != codex.get(field):
            errors.append(f"{name}: manifest field `{field}` is not synchronized")
    if codex.get("name") != name:
        errors.append(f"{name}: manifest name must match the plugin directory")
    version = codex.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        errors.append(f"{name}: version must be strict semver")
    if codex.get("skills") != "./skills/":
        errors.append(f"{name}: manifests must set `skills` to `./skills/`")

    interface = codex.get("interface")
    if not isinstance(interface, dict):
        errors.append(f"{name}: Codex manifest must contain `interface` metadata")
        interface = {}
    for field in REQUIRED_CODEX_INTERFACE_FIELDS:
        value = interface.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"{name}: missing Codex interface field `{field}`")
    if interface.get("category") != CATEGORIES[name]:
        errors.append(f"{name}: Codex interface category is wrong")

    skill_root = plugin_root / "skills" / name
    skill_path = skill_root / "SKILL.md"
    frontmatter, shared_text = load_skill_frontmatter(skill_path, errors)
    if set(frontmatter) != {"name", "description"}:
        errors.append(f"{name}: SKILL.md frontmatter may contain only name and description")
    if frontmatter.get("name") != name:
        errors.append(f"{name}: SKILL.md name must match its directory")
    skill_name = frontmatter.get("name")
    if not isinstance(skill_name, str) or len(skill_name) > 64 or not NAME_RE.fullmatch(skill_name):
        errors.append(f"{name}: invalid skill name")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        errors.append(f"{name}: description must be 1-1024 characters")
    elif "<" in description or ">" in description:
        errors.append(f"{name}: description must not contain angle brackets")

    for reference in sorted((skill_root / "references").glob("*.md")):
        shared_text += "\n" + reference.read_text(encoding="utf-8")
    for token in FORBIDDEN_SHARED_TOKENS:
        if token in shared_text:
            errors.append(f"{name}: shared instructions contain provider-specific token `{token}`")
    invocation = re.compile(rf"(?<![A-Za-z0-9])/{re.escape(name)}(?:\b|:)")
    if invocation.search(shared_text):
        errors.append(f"{name}: shared instructions contain Claude-style invocation syntax")

    openai_path = skill_root / "agents" / "openai.yaml"
    openai = load_yaml(openai_path, errors)
    openai_interface = openai.get("interface")
    if not isinstance(openai_interface, dict):
        errors.append(f"{name}: agents/openai.yaml must contain `interface`")
        openai_interface = {}
    for field in ("display_name", "short_description", "default_prompt"):
        value = openai_interface.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}: agents/openai.yaml is missing `{field}`")
    short_description = openai_interface.get("short_description", "")
    if isinstance(short_description, str) and not 25 <= len(short_description) <= 64:
        errors.append(f"{name}: openai short_description must be 25-64 characters")
    default_prompt = openai_interface.get("default_prompt", "")
    if isinstance(default_prompt, str) and f"${name}" not in default_prompt:
        errors.append(f"{name}: openai default_prompt must mention `${name}`")
    if (openai.get("policy") or {}).get("allow_implicit_invocation") is not True:
        errors.append(f"{name}: implicit invocation must be explicitly enabled")

    validate_plugin_files(plugin_root, errors)


def main() -> int:
    repo = parse_args().repo.resolve()
    errors: list[str] = []
    validate_marketplaces(repo, errors)
    for name in CROSS_PLATFORM_PLUGINS:
        validate_one_plugin(repo, name, errors)
    if errors:
        print("Cross-platform validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "Cross-platform validation passed for: "
        + ", ".join(CROSS_PLATFORM_PLUGINS)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
