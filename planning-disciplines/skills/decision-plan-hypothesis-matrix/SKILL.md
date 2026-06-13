---
name: decision-plan-hypothesis-matrix
description: Use BEFORE implementing a non-trivial decision-driven task where multiple outcomes are plausible — backtest planning, algorithm comparison, architecture choice, migration strategy, "should I build X or not". Trigger on phrases like "soll ich X bauen", "Backtest planen", "ich brauche eine Decision", "Algo-Varianten testen", "vor Implementation", "wie messe ich Erfolg", "max-Effort-Session", "Refactoring-Strategie wählen", "Compound-GO definieren". The skill produces a Plan-Notiz with an explicit Hypothesis-Matrix (each H + Gegenthese + Distinguishing Metric), Compound-GO-Logic, Out-of-Scope, and Done-Definition. Do NOT load for single-path implementations where there is no decision (e.g. "fix this typo", "add this column"), for brainstorming-/exploration-phase (use `superpowers:brainstorming` first), for plans without binary GO/NO-GO outcome (use `superpowers:writing-plans` for procedural multi-step plans without decision character), or when there is no measurable success criterion (then the task is exploration, not decision — defer planning until criterion exists). Encodes the 03.06.2026 pattern from Wolf-Vault ultimative-platform session — 5× applied across one day (Win-Rate analysis, E-1 debug, E-3 PSAR, E-3.1 R-Tier, E-4 Hängenbleiber-Diagnose) and prevented multiple Engineering-Tage of Wasted-Work — E-3/E-3.1 turned NO-GO via backtest before live-bot integration, E-4 original Score-Drift-Spec was invalidated by Pre-Code-Diagnose discovering OHLCV-Pipeline-Gap.
---

# Decision-Plan-Hypothesis-Matrix

> ✅ **PROMOTED 2026-06-03**: TDD-Pressure-Test Cycle 1 PASS (STRONG). RED-Subagent lieferte Pro/Contra-Liste mit Maximen-Verweisen aber keine formale Hypothesis-Matrix — kein Erfolgs-Kriterium VOR Analyse, keine Distinguishing-Metric-Tabelle, kein Compound-GO. GREEN-Subagent lieferte vollständige 7-Step Plan-Notiz mit 4 Hypothesen + Gegenthesen + Distinguishing-Metric + Compound-GO-Branches + Out-of-Scope + Done-Checklist. Auto-discoverable.

## Overview

Most non-trivial decisions have a story: "I think X is the right approach, let me try it." That story is often wrong, and you only find out after the implementation. This skill forces explicit hypothesis-formulation + falsification-criteria BEFORE code, so the decision is robust to your initial bias.

**Core principle:** Every substantial decision is a multi-hypothesis problem disguised as a single solution. Make the hypotheses explicit, and the decision becomes data-driven instead of intuition-driven.

## When to use

- Backtest planning (Trading algo, ML model variants, A/B framework)
- Algorithm selection (Trail-Stop A vs B, Optimizer X vs Y)
- Architecture choice with multiple valid paths
- Migration strategy with multiple risk profiles
- "Should I build X or not?" — gating before commitment
- Hard-won analysis sessions where you need to convince future-you of the verdict

## When NOT to use

- Single-path implementations (no decision character)
- Brainstorming / requirements-gathering (use `superpowers:brainstorming` first)
- Plans without GO/NO-GO outcome (use `superpowers:writing-plans` for procedural plans)
- Exploration phase where no success-criterion exists yet
- Time-boxed prototypes meant to fail-fast

## The 7-step procedure

### Step 1 — Erfolgs-Kriterium VOR Start

Write down the measurable outcome that determines GO/NO-GO. This must be:
- Concrete (Expectancy ≥ +0.05R, p<0.05, < 100ms latency)
- Falsifiable (not "improves UX" — "click-to-action < 200ms 95th percentile")
- Bounded (today's session, this PR, this experiment)

If you can't write the success-criterion, you're still in exploration. Defer.

### Step 2 — Liste 3-5 Hypothesen, jede mit Gegenthese

Each hypothesis = "I think X causes Y". Each Gegenthese = "but Z could also cause Y". The Gegenthese-Existenz is the lock against confirmation bias.

| # | Hypothese | Gegenthese |
|---|---|---|
| H1 | <claim about cause/effect> | <alternative cause for same effect> |
| H2 | ... | ... |

### Step 3 — Distinguishing Metric pro Hypothese

For each H/Gegenthese-Paar: what concrete metric, when measured, would tell you which one is true?

This is the most important step. If you can't define a Distinguishing Metric, the hypotheses are not actually distinct, and the whole framing is muddled.

| # | Hypothese | Gegenthese | Distinguishing Metric |
|---|---|---|---|
| H1 | A causes X | B causes X | Mean of X under condition-A only vs condition-B only — significantly different? |
| ... | ... | ... | ... |

### Step 4 — Compound-GO-Logik definieren

Most decisions are not 1-hypothesis. Define which combinations lead to GO vs NO-GO:

```
GO     ⇔ H1 confirmed AND H3 confirmed AND |Delta| ≥ X
NO-GO  ⇔ H1 refuted   OR  Sample-Size < N
Re-test ⇔ H2 inconclusive (CI overlaps 0)
```

Compound logic prevents "1 weak signal" from carrying a decision.

### Step 5 — Implementation-Plan (kurz)

Now that hypotheses + falsification are explicit, the implementation is just "the queries / code that produces the data". List the 3-5 implementation steps. Don't elaborate.

### Step 6 — Out-of-Scope explizit

Write what is NOT in scope. This is your gate against scope-creep mid-session. Examples:
- "Live deployment is NOT in scope — only sim-backtest"
- "Other algorithms (X, Y) are NOT in scope — only PSAR"
- "UI changes are NOT in scope — only backend logic"

### Step 7 — "When is the session done"

Concrete checklist (5-8 items max). Each item must be a yes/no that you can verify at session-end:
- ☐ Library implemented + N tests grün
- ☐ Backtest runs against production-DB without errors
- ☐ Result-Notiz with filled Verdict-Table
- ☐ Compound-Verdict explicit (GO / NO-GO / re-test)
- ☐ Roadmap-Item-Status updated

## Worked example (heute 03.06.2026 — E-3 PSAR-Trailing-Stop)

**Step 1 Erfolgs-Kriterium:**
> Verdict am Abend, ob PSAR-Trailing Expectancy hebt — über Replay der letzten 30 Tage virtual_trades vs Baseline.

**Step 2-3 Hypothesen-Matrix (Auszug):**

| # | Hypothese | Gegenthese | Distinguishing Metric |
|---|---|---|---|
| H1 | PSAR-Trail hebt 30% der 1-1.5R-Wins zu ≥2R | Trail schließt zu früh, Distribution ähnlich | Histogramm-Vergleich pnl_r-Verteilung Wins |
| H3 | Trail senkt WR nicht unter 40% | Trail erhöht Stop-Rate | WR mit Wilson-CI |

**Step 4 Compound-GO-Logik:**
```
E-3-B GO ⇔ H1 confirmed AND H3 confirmed AND Delta-Expectancy ≥ +0.05R
```

**Step 5 Implementation:**
1. Library `core/indicators/psar_trailing_stop.py` + TDD-Tests
2. Backtest-Script gegen 30d virtual_trades
3. Result-Notiz mit Verdict-Tabelle

**Steps 6-7:** wie üblich.

**Outcome:** Backtest widerlegte H1 + H3 → Compound-Verdict NO-GO. **Ohne Plan-Matrix wäre die nächste Phase Live-Bot-Integration gewesen** (= 1 Tag Engineering für netto-negativen Algorithmus).

## Anti-patterns

- ❌ Hypothesis-Liste ohne Gegenthese ("I think X because reasons") — entfernt die Falsifikations-Möglichkeit
- ❌ Distinguishing Metric "wir schauen mal die Daten an" — nicht konkret genug, lässt confirmation bias durch
- ❌ Single-Hypothesis Compound-GO ("wenn H1 confirmed → GO") — eine Aussage entscheidet ist fragil, immer ≥2 Bedingungen
- ❌ Implementation-Steps mit > 8 Zeilen — Plan wird Spec, verliert Decision-Charakter
- ❌ Out-of-Scope leer — fehlt das Scope-Creep-Schutzschild
- ❌ Erfolgs-Kriterium nachträglich anpassen wenn Daten nicht passen ("eigentlich ist Y das echte Kriterium") — Decision-Hygiene gone

## Template-Snippet

```markdown
# <Topic> — Plan YYYY-MM-DD

## Erfolgs-Kriterium
> <one measurable sentence>

## Hypothesen-Matrix
| # | Hypothese | Gegenthese | Distinguishing Metric | Konsequenz wenn H | Konsequenz wenn ¬H |
|---|---|---|---|---|---|
| H1 | ... | ... | ... | GO-Hint | NO-GO-Hint |
| ... | ... | ... | ... | ... | ... |

## Compound-GO-Logik
- **GO** ⇔ <combination>
- **NO-GO** ⇔ <combination>
- **Re-test** ⇔ <combination>

## Implementation-Plan (max 8 Steps)
1. ...

## Out-of-Scope (heute)
- ...

## Wann ist Session done
- ☐ ...
```

## Skill-Composition

- `superpowers:brainstorming` — runs BEFORE this skill if requirements are unclear
- `superpowers:writing-plans` — alternative for procedural plans WITHOUT decision-character
- `superpowers:test-driven-development` — runs AFTER for the implementation step
- `compound-gate-over-single-metric-DRAFT` — related but smaller-scope (no Hypothesis-Matrix part)

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-03 (PASS — STRONG)

**Scenario** (Wolf-typische ultimative-platform-Frage):
> Ich überlege ob ich einen RSI-Divergenz-Filter (14-Bar bullische Divergenz als Pflicht für Long-Signal) als Layer-3 baue. Soll ich das bauen?

**RED-Subagent** (ohne Skill): Lieferte strukturierte Pro/Contra-Liste mit Maximen-Verweisen (Cardwell, Backtest-First, Münzwurf-Problem). Implizit am Ende „3 Kriterien Compound-GO" formuliert. Self-Reflection ehrlich: „keine formale Hypothesis-Matrix, keine echte H/Gegenthese mit Distinguishing-Metric, Erfolgs-Kriterien während (nicht vor) der Antwort konstruiert aus Bauchgefühl". Hätte Wolf gefolgt, wären 5 unkalibrierte Risiken offen geblieben (Divergenz-Definition-Drift, WR-only-Metrik, Sample-Size, Overfitting-Tür, implizite Layer-1+2-Filterbarkeits-Annahme).

**GREEN-Subagent** (mit Skill): Lieferte vollständige Plan-Notiz im Skill-Format:
- Erfolgs-Kriterium konkret + falsifizierbar (Δ-Expectancy ≥ +0.05R, N ≥ 80, Wilson-LB-WR ≥ 40%)
- 4 Hypothesen mit echten Gegenthesen + konkreten Distinguishing-Metrics (Bootstrap-CI, Wilson-CI, Retention-Anteil, Per-Instrument-Top-2)
- Compound-GO mit AND-Verknüpfung über alle 4 H, plus Re-test-Branch für grenzwertige Fälle
- Out-of-Scope mit 7 expliziten Ausschlüssen (Live-Bot zuerst gegated)
- Done-Checklist 8 verifizierbare Items
- Keine 7 Schritte übersprungen

**Verdict**: STRONG PASS. RED zeigt klares Anti-Pattern (Pro/Contra statt Matrix), GREEN zeigt qualitativen Sprung. Promotion erfolgt.

**Refactor angewendet**: keine Code-Änderungen — Polish-Items werden als Cycle-2-Backlog dokumentiert (nicht-blocking).

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Heuristik wann 3 vs 5 Hypothesen** — Skill sagt "3-5", aber gibt keine Bottom-Up-Regel. Vorschlag: "minimum 1 Edge-H + 1 Robustness-H + 1 Tradability-H" (aus GREEN-Subagent-Vorschlag)
2. **Power-Check-Substep in Step 1** — bei Statistik-getriebenen Decisions (Bootstrap-CI, Wilson) zusätzlich Power-Analyse: "ist N realistisch für Effect-Size E mit Significance-Level α?"
3. **Out-of-Sample-Validation als Pflicht im Re-test-Branch** — derzeit nur implizit, sollte explizit als Decision-Hygiene dokumentiert sein
4. **Live-Anwendungs-Log** — Tracking-Mechanik um mitzuzählen wie oft das Skill triggert (für künftige Promotion-Audit-Logs)

Iron-Law: Cycle-2-Items werden vor Anwendung mit failing-test-first behandelt, nicht als „silent edit".
