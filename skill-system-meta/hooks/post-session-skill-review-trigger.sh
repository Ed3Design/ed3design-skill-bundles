#!/bin/bash
# post-session-skill-review-trigger.sh
#
# UserPromptSubmit-Hook. Detects session-end signals in user prompts and
# reminds Claude to load the post-session-skill-review skill.
#
# Pattern: when the user says "remember", "wrap up", "session done", "Tagesabschluss",
# "session schließen", or similar, this is the trigger for the ABC-skill-review
# process — but Claude often forgets. Hook = mechanical defense.
#
# Skill: post-session-skill-review
# Behavior: warn-only (exit 0). Stderr message lands in Claude's context.

set -u

input=$(cat)
prompt=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt', ''))" 2>/dev/null)

# Skip empty prompts
[ -z "$prompt" ] && exit 0

# Session-end signal patterns (German + English)
session_end_pattern='[Rr]emember|[Ww]rap.up|[Ss]ession.(done|end|close|schließ|abschl)|[Tt]agesabschluss|end.of.day|[Ww]as.haben.wir.heute|ABC.[Ff]ilter|skill.[Rr]eview|post.session'

if echo "$prompt" | grep -qE "$session_end_pattern"; then
    echo "🎓 post-session-skill-review-trigger: session-end signal detected in user message." >&2
    echo "    Load 'skill-system-meta:post-session-skill-review' and apply ABC-filter" >&2
    echo "    (A=repeatable pattern with steps, B=would prevent Claude error, C=transferable" >&2
    echo "    beyond single project) to all recurring patterns from today's session." >&2
    echo "    Output format: skill candidates ✅✅✅ / Borderline (memory or CLAUDE.md instead)" >&2
    echo "    / One-offs (no skill). Delivery: structured list, then ask user which to build." >&2
fi

exit 0
