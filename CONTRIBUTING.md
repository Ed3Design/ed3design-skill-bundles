# Contributing

Thanks for considering a contribution. This repository follows a few specific conventions because skills, hooks, and sub-agents need to be predictable for Claude Code to load and apply them correctly.

## Quick Start

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
cd ed3design-skill-bundles

# Validate all bundles
python3 -c "
import json, os
for b in os.listdir('.'):
    p = f'{b}/.claude-plugin/plugin.json'
    if os.path.exists(p):
        m = json.load(open(p))
        print(f'✅ {b}: name={m[\"name\"]}')
"
```

## Adding a Skill to a Bundle

### Decide on the right bundle

A skill belongs in a bundle if it matches one of the 6 thematic domains:

- `token-savers` — token optimization (vision/PDF/web/vault/schema/diff)
- `code-quality` — code review, Git hygiene, code patterns
- `planning-disciplines` — roadmap, decision-making, reality inventory
- `async-forensik` — asyncio + container debugging
- `schema-discipline` — SQL/schema bug-class prevention
- `skill-system-meta` — skill-building itself

If your skill doesn't fit any of these, propose a new bundle in an issue first.

### Skill format

Each skill lives in `<bundle>/skills/<skill-name>/SKILL.md` with this frontmatter:

```markdown
---
name: <skill-name>
description: Use when <trigger conditions>. <one-line value proposition>. Trigger on phrases like "<phrase 1>", "<phrase 2>". Do NOT load for <anti-trigger conditions>.
---

# <Skill Title>

> ✅ **PROMOTED <date>** — TDD-Pressure-Test PASS. <one-line empirical result>.

## When to use
...

## When NOT to use
...

## How to use
...

## Anti-patterns
...

## Background: TDD-Verlauf
...
```

The `description` field is critical — Claude Code uses it for auto-discovery. Make sure:
- It contains specific trigger phrases users would type
- It contains explicit `Do NOT load for ...` patterns to prevent over-triggering
- It's specific enough that the skill name + description tell you the value in 2 seconds

### TDD Promotion Cycle

Before a skill is merged, it must pass the TDD promotion cycle (see `skill-system-meta/skills/skill-tdd-promotion-workflow`):

1. **RED subagent** (without skill) tries to solve the trigger scenario → demonstrates the natural anti-pattern
2. **GREEN subagent** (with skill) tries the same scenario → demonstrates the skill's value
3. Both subagents reflect on the skill (Self-Reflection section)
4. If RED shows clear anti-pattern AND GREEN shows clear compliance → PROMOTE to GA
5. Otherwise: refactor skill and re-run cycle

This prevents low-value skills from polluting the auto-discovery namespace.

## Adding a Sub-Agent

Sub-agents live in `<bundle>/agents/<agent-name>.md`:

```markdown
---
name: <agent-name>
description: <when to dispatch this agent>
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: default
---

# <Agent Title>

You are a <role> sub-agent. You <one-line purpose>.

## Workflow
...

## Anti-Patterns to Avoid
...

## Cross-References
...
```

Register the agent in the bundle's `plugin.json`:

```json
{
  "agents": ["./agents/<agent-name>.md"]
}
```

Tool limits matter: a read-only reviewer agent should NOT have Write/Edit access. Be deliberate.

## Adding a Hook

Hooks live in `<bundle>/hooks/<hook-name>.sh` (executable bash scripts):

```bash
#!/bin/bash
# <hook-name>.sh — <one-line description>
#
# <Event>-Hook (e.g. PreToolUse Bash).
# Skill: <related skill>
# Behavior: <warn-only / block / audit>

set -u

input=$(cat)
# Parse PreToolUse JSON via stdin
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Match trigger pattern
if echo "$command" | grep -qE '<pattern>'; then
    echo "⚠️  <hook-name>: <warning>" >&2
    echo "    <recommendation>" >&2
fi

exit 0
```

Register in `hooks/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/<hook-name>.sh"
          }
        ]
      }
    ]
  }
}
```

Register in `plugin.json`:

```json
{
  "hooks": "./hooks/hooks.json"
}
```

**Design principle**: hooks should warn, not block. Exit 0 with stderr is the standard pattern. Hard blocks (exit 2) frustrate users; warnings land in Claude's context and inform future tool calls.

## Adding a Python Tool

Python tools live in `<bundle>/tools/<tool-name>.py`. Style conventions:

- Shebang `#!/usr/bin/env python3`
- Docstring at the top with usage examples
- `argparse` for CLI args
- JSON output as primary format (token-efficient)
- Use `pathlib.Path` instead of string path operations
- Standard library + 1-2 well-tested deps only (PIL, bs4, certifi)

When a skill references a tool, use the portable path pattern:

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/<tool-name>.py
```

This works both in the plugin context and when installed locally.

## Pull Request Workflow

1. Fork the repo
2. Create a feature branch: `git checkout -b add-<bundle>-<skill-name>`
3. Add your skill / hook / agent / tool
4. Update the bundle's `README.md` with a row in the trigger table
5. Update `plugin.json` if you added a hook or agent
6. Bump the bundle's `version` (semver: patch for fixes, minor for additions, major for breaking)
7. Open a PR with:
   - **Title**: `feat(<bundle>): add <skill-name>`
   - **Body**: empirical value proposition (what it prevents, with concrete metrics if available) + TDD cycle result (RED vs GREEN comparison)

## Code of Conduct

Be kind. Be direct. Engineering disciplines emerge from real practice — share what worked, share what failed, share the reasoning. No personal attacks, no gatekeeping.

## License

By contributing, you agree your contributions will be licensed under the same MIT license as the rest of the repo.
