#!/bin/bash
PY=$(command -v python3 || command -v python)
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
# Behavior: warn-only (exit 0). Warning goes out as hookSpecificOutput.additionalContext
# on stdout (not plain stderr) — only additionalContext reliably reaches Claude's context.

set -u

input=$(cat)
prompt=$(echo "$input" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt', ''))" 2>/dev/null)

# Skip empty prompts
[ -z "$prompt" ] && exit 0

# Session-end signal patterns (German + English). The gap between "session"
# and its closing verb is a bounded character class (up to ~40 chars, any
# direction), not a single "." — real sentences ("lass uns die Session jetzt
# abschließen") have several words in between, which a single-char gap misses.
# Case-insensitive (-i below) so capitalized German nouns ("Ende") still match.
session_end_pattern='remember|wrap.?up|session[^\n]{0,40}(done|end|close|schlie|abschl|beend)|(schlie|abschl|beend)[^\n]{0,40}session|tagesabschluss|end.of.day|was.haben.wir.heute|abc.filter|skill.review|post.session'

if echo "$prompt" | grep -qiE "$session_end_pattern"; then
    "$PY" -c "
import json
ctx = (
    'post-session-skill-review-trigger: session-end signal detected in user message. '
    \"Load 'skill-system-meta:post-session-skill-review' and apply the ABC filter \"
    '(A=repeatable pattern with steps, B=would prevent a Claude error, C=transferable '
    'beyond this one project) to every recurring pattern from today\\'s session. '
    'Output format: skill candidates / borderline (memory or CLAUDE.md instead) / '
    'one-offs (no skill). Deliver as a structured list, then ask the user which to build.'
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': ctx,
    }
}))
"
fi

exit 0
