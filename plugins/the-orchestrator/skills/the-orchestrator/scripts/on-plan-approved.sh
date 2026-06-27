#!/bin/bash
# Post-plan-approval hook for orchestrator sessions.
# Injects TDD context after ExitPlanMode succeeds.
# Only fires in orchestrator sessions (ORCHESTRATOR_SESSION=1).

cat >/dev/null   # consume stdin

if [ "${ORCHESTRATOR_SESSION}" = "1" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: "This project follows test-first development via the /tdd skill. All implementation nodes go through /tdd unless the change is trivially small (single-line fix, config tweak, rename). The /tdd skill is skipped only in those narrow cases."
    }
  }'
fi
exit 0
