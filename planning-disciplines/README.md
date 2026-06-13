# planning-disciplines

> Planning + decision disciplines before any multi-phase project.

## Skills (10)

| Skill | Phase |
|---|---|
| `brain-dump-to-phased-roadmap` | Brain dump → structured phase roadmap |
| `decision-plan-hypothesis-matrix` | Hypothesis matrix for decision-making |
| `roadmap-phase-execution-verify-first` | Reality inventory before phase execution (spec-drift detection) |
| `plan-execution-state-drift-precheck` | State-drift check before plan execute |
| `plan-execution-stack-mode-precheck` | Stack-mode check (dev vs prod vs test) before execute |
| `strategic-questions-before-code-touch` | 2-4 strategic questions via AskUserQuestion before code |
| `strategic-proposal-vault-persistence-check` | Session-end: vault persistence of structured outputs |
| `briefing-source-triangulation` | Briefing from 3+ sources instead of single-source |
| `compound-gate-over-single-metric` | Multi-metric gate instead of single-metric trigger |
| `domain-rules-anti-patterns-first` | Document anti-patterns first, then derive rules |

## Strategic Leverage

These 10 skills systematically prevent:
- Wished-for implementation (spec drift on same-day specs)
- Single-source briefing bias
- Hypotheses without falsification tests
- Code touch without strategic decision lock

Empirically measured: ~30-40% implementation effort saved on vision-spec execution.

## 🤖 Sub-Agent (1)

| Agent | Description |
|---|---|
| `planning-assistant` | Reality-inventory + strategic-questions pipeline before multi-phase features. 4 phases (drift table → user-decision ID → question block → implementation gate). Sonnet model |

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/planning-disciplines/skills"/* ~/.claude/skills/
```

## License

MIT.
