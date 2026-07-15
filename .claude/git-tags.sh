#!/bin/sh
# otelHeadersHelper: emit the current repo + branch as OTLP HTTP headers so the
# ingest server can attribute Claude Code telemetry per repo/branch. Claude Code
# runs this from the repo working directory at startup and on a ~29-min debounce
# (CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS), on BOTH the terminal CLI and the
# desktop app — the one attribution channel the desktop app doesn't strip.
#
# POSIX sh (no bashisms) so it runs identically under bash 3.2 (system macOS),
# Homebrew bash, or zsh-invoked-as-sh. Commit with the executable bit set.
url="$(git remote get-url origin 2>/dev/null)"; url="${url%.git}"
# last two path segments of the remote → "org/repo" (handles git@ and https URLs)
repo="$(printf '%s' "$url" | awk -F'[/:]' 'NF>=2{print $(NF-1)"/"$NF}')"
[ -z "$repo" ] && repo="$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ "$branch" = "HEAD" ] && branch="detached-$(git rev-parse --short HEAD 2>/dev/null)"
# keep only header/URL-safe characters
repo="$(printf '%s' "$repo" | tr -cd 'A-Za-z0-9._/-')"
branch="$(printf '%s' "$branch" | tr -cd 'A-Za-z0-9._/-')"
printf '{"X-Git-Repo":"%s","X-Git-Branch":"%s"}' "$repo" "$branch"
