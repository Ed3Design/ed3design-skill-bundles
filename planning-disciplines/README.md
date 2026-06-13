# planning-disciplines

> Planning + Decision-Disziplinen vor jedem Multi-Phase-Projekt.

## Skills (10)

| Skill | Phase |
|---|---|
| `brain-dump-to-phased-roadmap` | Brain-Dump → strukturierte Phasen-Roadmap |
| `decision-plan-hypothesis-matrix` | Hypothesen-Matrix für Decision-Making |
| `roadmap-phase-execution-verify-first` | Reality-Inventur vor Phase-Execution (Spec-Drift-Detection) |
| `plan-execution-state-drift-precheck` | State-Drift-Check vor Plan-Execute |
| `plan-execution-stack-mode-precheck` | Stack-Mode-Check (Dev vs Prod vs Test) vor Execute |
| `strategic-questions-before-code-touch` | 2-4 strategische Fragen via AskUserQuestion vor Code |
| `strategic-proposal-vault-persistence-check` | Session-Ende: Vault-Persistierung strukturierter Outputs |
| `briefing-source-triangulation` | Briefing aus 3+ Quellen statt Single-Source |
| `compound-gate-over-single-metric` | Multi-Metrik-Gate statt Single-Metric-Trigger |
| `domain-rules-anti-patterns-first` | Anti-Patterns zuerst dokumentieren, dann Rules ableiten |

## Strategischer Hebel

Diese 10 Skills verhindern systematisch:
- Wished-for-Implementation (Spec-Drift bei Same-Day-Specs)
- Single-Source-Briefing-Bias
- Hypothesen ohne Falsification-Test
- Code-Touch ohne Strategic-Decision-Lock

Empirisch belegt: ~30-40% Implementations-Aufwand gespart bei Vision-Spec-Execution (Wolf 12.06. Phase B+C+D).

## 🤖 Sub-Agent (1)

| Agent | Beschreibung |
|---|---|
| `planning-assistant` | Reality-Inventur + Strategic-Questions Pipeline vor Multi-Phase-Features. 4 Phasen (Drift-Tabelle → Wolf-Decision-ID → Frage-Block → Implementation-Gate). Sonnet-Modell |

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/planning-disciplines/skills"/* ~/.claude/skills/
```

## Lizenz

MIT.
