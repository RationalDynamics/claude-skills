#!/usr/bin/env bash
# Install every plugin in the devo-skills marketplace in one go.
#
# Usage:
#   ./install-all.sh                 # add the GitHub marketplace, then install all
#   ./install-all.sh <path-or-url>   # override the marketplace source (e.g. a local checkout)
#
# The plugin list is read straight from .claude-plugin/marketplace.json, so this
# stays in sync automatically as skills are added or removed — no hardcoded list.
#
# Skills load at session start: start a fresh Claude Code session after this runs.
set -euo pipefail

NAME="devo-skills"
SRC="${1:-https://github.com/RationalDynamics/claude-skills}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CATALOG="$DIR/.claude-plugin/marketplace.json"

command -v claude >/dev/null 2>&1 || { echo "error: 'claude' CLI not found on PATH" >&2; exit 1; }
command -v jq     >/dev/null 2>&1 || { echo "error: 'jq' not found on PATH" >&2; exit 1; }
[ -f "$CATALOG" ] || { echo "error: catalog not found at $CATALOG" >&2; exit 1; }

# Add the marketplace, or refresh it if it is already registered.
echo "==> registering marketplace: $SRC"
claude plugin marketplace add "$SRC" 2>/dev/null || claude plugin marketplace update "$NAME"

# Install every plugin listed in the catalog.
while IFS= read -r p; do
  echo "==> installing $p@$NAME"
  claude plugin install "$p@$NAME"
done < <(jq -r '.plugins[].name' "$CATALOG")

echo
echo "All plugins installed. Start a fresh Claude Code session to load the new skills."
