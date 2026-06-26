#!/usr/bin/env bash
# SessionStart hook for neuralize
# Checks if a neuralize reload is pending, injects the selected context,
# and cleans up all temporary state.

PENDING_FILE="/tmp/.neuralize_pending.json"

# Exit silently if no pending neuralize
if [ ! -f "$PENDING_FILE" ]; then
  exit 0
fi

# Parse the pending state
PENDING=$(cat "$PENDING_FILE" 2>/dev/null)
IS_PENDING=$(echo "$PENDING" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pending', False))" 2>/dev/null)

if [ "$IS_PENDING" != "True" ]; then
  exit 0
fi

# Extract paths
RELOAD_FILE=$(echo "$PENDING" | python3 -c "import sys,json; print(json.load(sys.stdin)['reload_file'])" 2>/dev/null)
SESSION_DIR=$(echo "$PENDING" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_dir'])" 2>/dev/null)

if [ ! -f "$RELOAD_FILE" ]; then
  # Reload file missing — clean up and exit
  rm -f "$PENDING_FILE"
  rm -f "/tmp/.breakpoint_active_session"
  exit 0
fi

# Read the reload content
CONTENT=$(cat "$RELOAD_FILE")

# Clean up: session directory, pending state, active session marker
rm -rf "$SESSION_DIR"
rm -f "$PENDING_FILE"
rm -f "/tmp/.breakpoint_active_session"

# Inject the restored context as a systemMessage
# The hook output format: JSON with systemMessage field
python3 -c "
import json, sys
content = sys.stdin.read()
print(json.dumps({'systemMessage': content}))
" <<< "$CONTENT"
