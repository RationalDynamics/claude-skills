#!/usr/bin/env bash
# SessionStart hook for the `evict` skill.
# If an evict reload is pending, inject the kept (verbatim / summarized) context
# via hookSpecificOutput.additionalContext (the ONLY SessionStart channel that
# reaches the model — `systemMessage` is not a valid SessionStart output field and
# is silently discarded) and clean up all temporary state. No-op otherwise.

PENDING_FILE="/tmp/.evict_pending.json"

[ -f "$PENDING_FILE" ] || exit 0

PENDING=$(cat "$PENDING_FILE" 2>/dev/null)
IS_PENDING=$(printf '%s' "$PENDING" | python3 -c "import sys,json;
try: print(json.load(sys.stdin).get('pending', False))
except Exception: print(False)" 2>/dev/null)

[ "$IS_PENDING" = "True" ] || exit 0

RELOAD_FILE=$(printf '%s' "$PENDING" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reload_file',''))" 2>/dev/null)
WORK_DIR=$(printf '%s' "$PENDING" | python3 -c "import sys,json; print(json.load(sys.stdin).get('work_dir',''))" 2>/dev/null)

if [ ! -f "$RELOAD_FILE" ]; then
  # Marker said a reload was pending but the staged file is gone. Don't silently
  # drop it — surface it via additionalContext (SessionStart has no `systemMessage`
  # field; it is discarded), so the failure actually reaches the model/user.
  rm -f "$PENDING_FILE"
  python3 -c "import json; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '[evict] A context reload was staged but its content file was missing at /clear time — nothing was restored. Re-run /evict.'}}))"
  exit 0
fi

# Claude Code caps hook `additionalContext` at 10,000 characters: above that it
# persists the full text to a file and injects only a preview, so large kept-context
# silently fails to restore. Inline only payloads that stay safely under the cap
# (9000 bytes leaves margin for byte-vs-char width and JSON escaping); for larger
# ones, preserve the reload file at a stable path and inject a short pointer so the
# model reads the FULL content on its next turn (the read path has no inline cap).
CONTENT_SIZE=$(wc -c < "$RELOAD_FILE" | tr -d ' ')
INLINE_LIMIT=9000

emit() { python3 -c "import json,sys; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': sys.stdin.read()}}))"; }

if [ "$CONTENT_SIZE" -le "$INLINE_LIMIT" ]; then
  # Small enough to inline directly — seamless, no tool call.
  CONTENT=$(cat "$RELOAD_FILE")
  [ -n "$WORK_DIR" ] && rm -rf "$WORK_DIR"
  rm -f "$PENDING_FILE"
  printf '%s' "$CONTENT" | emit
else
  # Too large to inline without harness truncation — preserve + point at the file.
  STABLE="/tmp/evict_reload_last.md"
  cp "$RELOAD_FILE" "$STABLE"
  [ -n "$WORK_DIR" ] && rm -rf "$WORK_DIR"
  rm -f "$PENDING_FILE"
  printf '%s' "# Restored Context (via /evict)

Your kept context from before /clear is ${CONTENT_SIZE} bytes — too large to inline without truncation. It was saved IN FULL to:

    ${STABLE}

Read that file in full now, before doing anything else, and treat its contents as your restored session context (the blocks you chose to keep)." | emit
fi
