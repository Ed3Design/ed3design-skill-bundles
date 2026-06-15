# skill-system-meta

> Skill-system disciplines for Claude Code power users who build their own skills.

## Skills (5)

| Skill | Trigger | Value |
|---|---|---|
| `post-session-skill-review` | Session end, "remember", "wrap up" | ABC filter identifies skill candidates from recurring patterns |
| `skill-tdd-promotion-workflow` | Promote DRAFT skill to GA | RED+GREEN sub-agent dispatch validates skill value before auto-discovery |
| `subagent-mode-selection-continuous-vs-review-between` | Multi-sub-agent dispatch | Mode selection: continuous-flow vs review-between (TDD discipline) |
| `subagent-self-reflection-prompt-pattern` | Sub-agent prompt design | Mandatory `## Skill-Self-Reflection` section yields cycle-2 polish items |
| `design-first-iteration` | Before any creative work | Brainstorming → design → implementation, not straight to code |

## Installation

```bash
# Via marketplace:
/plugin marketplace add Ed3Design/ed3design-skill-bundles
/plugin install skill-system-meta@ed3design-skill-bundles

# Manually:
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/skill-system-meta/skills"/* ~/.claude/skills/
```

## Pattern Compound

These 5 skills are **cumulatively** valuable: post-session-review identifies candidates → design-first-iteration brainstorms them → skill-tdd-promotion validates them → sub-agent patterns optimize dispatch. Investment pays off after ~3 re-applications per skill (empirically measured).

## License

MIT.
