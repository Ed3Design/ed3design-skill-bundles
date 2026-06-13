# skill-system-meta

> Skill-System-Disziplinen für Claude-Code-Power-User die eigene Skills bauen.

## Skills (5)

| Skill | Trigger | Wert |
|---|---|---|
| `post-session-skill-review` | Session-Ende, „remember", „wrap up" | ABC-Filter erkennt Skill-Kandidaten aus wiederkehrenden Patterns |
| `skill-tdd-promotion-workflow` | DRAFT-Skill zu GA promoten | RED+GREEN-Subagent-Dispatch validiert Skill-Wert vor Auto-Discovery |
| `subagent-mode-selection-continuous-vs-review-between` | Multi-Subagent-Dispatch | Mode-Auswahl: continuous-flow vs review-between (Iron-Law-Disziplin) |
| `subagent-self-reflection-prompt-pattern` | Subagent-Prompt-Design | Pflicht-Sektion „## Skill-Self-Reflection" liefert Cycle-2-Polish-Items |
| `design-first-iteration` | Vor jedem creative Work | Brainstorming → Design → Implementation, nicht direkt zu Code |

## Installation

```bash
# Via marketplace (wenn registered):
/plugin install ed3design-skill-bundles/skill-system-meta

# Manuell:
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/skill-system-meta/skills"/* ~/.claude/skills/
```

## Pattern-Compound

Diese 5 Skills sind **kumulativ** wertvoll: post-session-review identifiziert Kandidaten → design-first-iteration brainstormt sie → skill-tdd-promotion validiert sie → subagent-Patterns optimieren Dispatch. Investition macht sich nach ~3 Re-Anwendungen pro Skill bezahlt (empirisch belegt 11.06.2026 8-Skill-Promotion-Block).

## Lizenz

MIT. Discipline-Discovery aus 4 Wochen Wolf-Vault-Practice formalisiert.
