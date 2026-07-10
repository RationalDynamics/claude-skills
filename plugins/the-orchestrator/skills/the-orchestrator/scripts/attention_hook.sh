#!/bin/bash
# Orchestrator attention hook.
#
# Invoked by a node session's Claude Code hooks to report whether that session is
# currently blocked waiting on the user. The orchestrator viewer server turns this
# into a blinking red "needs input" dot on the node.
#
# Usage: attention_hook.sh <port> <node_id> <state>
#   state = needs_input  (from the Notification hook)
#         | clear         (from UserPromptSubmit / Stop / SessionEnd)
#
# The Claude Code hook JSON payload arrives on stdin; we drain it (the matcher
# on the Notification hook already scopes this to permission/idle/needs-input
# events, so we don't need to parse it) and POST the state to the server.
PORT="$1"
NODE_ID="$2"
STATE="${3:-needs_input}"

cat >/dev/null 2>&1   # drain stdin (hook payload) so Claude Code isn't blocked

[ -n "$PORT" ] && [ -n "$NODE_ID" ] || exit 0

curl -s --max-time 2 -X POST \
  "http://localhost:${PORT}/api/attention/${NODE_ID}" \
  -H 'Content-Type: application/json' \
  -d "{\"state\":\"${STATE}\"}" >/dev/null 2>&1 || true

exit 0
