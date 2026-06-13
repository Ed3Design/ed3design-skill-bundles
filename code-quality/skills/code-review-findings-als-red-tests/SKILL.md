---
name: code-review-findings-als-red-tests
description: Use when a code-review-subagent (z.B. feature-dev:code-reviewer) has returned Critical/Important findings on a feature-commit and you're about to write fixes. Standard-default is "direkt-fix, kein neuer Test". This skill says: jedes Finding ist selbst ein Test-Case — schreibe einen RED-Test der das Bug-Verhalten zeigt, dann GREEN-Fix. Verhindert Regressions + dokumentiert das Bug-Pattern für künftige Reviews. Trigger on phrases like "Code-Review-Findings fixen", "Critical-Fix einbauen", "Review-Subagent fand C1/I1/I2", "Sonnet-Subagent-Output zu Fix umwandeln", "Review-Cycle abschließen". Do NOT load for trivial style-Findings (typo, unused-import), for Findings ohne reproducible code-path (perf-Hints, future-proofing), for Code wo TDD bewusst skipped wurde (user-confirmed), or wenn der Subagent KEINE Findings hatte.
---

# Code-Review-Findings als RED-Tests

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. RED zeigte „Direct-Edit + Spot-Check" als Default, kein Regression-Schutz, ~45min total; GREEN schrieb 4 bug-pattern-Tests (test_sl_knocked_out_renders_warning_not_zero_eur etc.) mit RED-Verify-Pflicht, +19min für Regression-Schutz. Cycle 2 Polish: Decision-Tree „RED-Test passt unexpected", Finding-Cluster-Heuristik (zusammen-Commit vs getrennt).

## Overview

Code-Review-Subagent (Sonnet) returnt typisch Findings als:
- **Critical/Important/Minor** mit Confidence-Score
- File-Path + Line-Number  
- „Befund + Was statt dessen"-Erklärung

Standard-Default beim Empfangen: direkt fix-Commit mit Edit. **Problem**: ohne Regression-Test kann der gleiche Bug nach Refactoring wieder auftauchen. Plus: das Bug-Pattern wird nicht für künftige Reviews lernbar dokumentiert.

**Fix-Pattern dieser Skill**: jedes Finding zu RED-Test umwandeln, dann GREEN-Implementation. Drei Outcomes:

1. **Regression-Schutz**: künftiges Refactoring kann nicht den gleichen Bug wieder einführen
2. **Bug-Pattern-Dokumentation**: der Test-Name + Docstring macht den Bug-Pattern referenzierbar
3. **Confidence-Verifikation**: schreibt der RED-Test fail wirklich genau das was Sonnet beschrieben hat? Wenn nicht — Finding ist unklar oder Sonnet hat überreagiert

## When to use

Trigger-Phrasen:
- „Code-Review-Findings fixen"
- „Critical-Fix einbauen"
- „Review-Subagent fand C1 / I1 / I2"
- „Sonnet-Subagent-Output zu Fix umwandeln"
- „Review-Cycle abschließen"

Konkrete Signale:
- Subagent hat strukturierte Findings retourniert (nicht nur Vibes)
- Mindestens 1 Critical oder Important
- Findings haben reproducible Code-Paths (File + Line)
- Code unter Test (nicht throwaway-Script)

## When NOT to use

- **Trivial Style-Findings**: Typo, unused-Import → einfach fixen
- **Future-Proofing-Hints**: „bei skalierung wäre Y besser" → kein reproducible Bug
- **Perf-Hints ohne Benchmark-Test**: „könnte schneller sein" → nicht testbar
- **TDD bewusst skipped**: User-Override „kein Test, direkt fix"
- **Keine Findings**: Subagent gab grünes Licht

## How to use

### Step 1 — Findings parsen + priorisieren

Pro Finding:
- **Schwere**: C/I/M
- **File + Line**: konkret
- **Pattern-Name**: extrahiere „was war der Bug" (z.B. „Knockout-SL-als-0.00-EUR-gerendert")
- **Reproducible**: kann ich das in einem Test reproduzieren? (Wenn nein → Anti-Pattern)

### Step 2 — RED-Test pro Finding schreiben

Test-Struktur:
- **Test-Name**: bug-pattern-beschreibend (z.B. `test_sl_knocked_out_renders_warning_not_zero_eur`)
- **Docstring**: Sonnet-Befund + Wolf-Impact zitieren
- **Assert**: das Anti-Pattern muss NICHT auftauchen (z.B. `assert "0.00 EUR" not in sl_line`)

### Step 3 — Verify RED

Run die neuen Tests gegen aktuelles Production-Code → MUST fail. Wenn nicht:
- Finding war fälschlich (Subagent-Halluzination)
- Test-Assertion ist zu weich
- Bug-Pattern war nicht so wie beschrieben

In allen 3 Fällen: NICHT GREEN schreiben — stattdessen mit Subagent oder User klären.

### Step 4 — GREEN-Implementation

Minimaler Fix der die Tests grün macht. Pattern wie `superpowers:test-driven-development`.

### Step 5 — Commit-Message dokumentiert Findings

```
fix(<scope>): Code-Review-Findings — <kurz-Liste>

C1 (Critical) — <Befund kurz>
Fix: <Was geändert>

I1 (Important) — <Befund>
Fix: <Was geändert>

TDD: N neue RED→GREEN-Tests in <test-file>.
```

Macht den Fix-Commit reviewable + zeigt dass Review-Findings systematisch verarbeitet wurden.

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Direkt-fix ohne Test | RED-Test pro Finding |
| Test schreiben aber Sonnet-Befund nicht zitieren | Docstring mit Sonnet-Befund-Auszug |
| Generischer Test-Name (`test_fix_critical_1`) | Bug-Pattern-beschreibend (`test_sl_knocked_out_renders_warning_not_zero_eur`) |
| Mehrere Findings in einem Test bündeln | Pro Finding ein Test (oder eine Test-Klasse) |
| RED-Phase überspringen („Test passes immediately") | Run Tests gegen aktuelles Code MUST fail vor Fix |
| Findings ignorieren weil „Sonnet überreagiert" | Klären statt skippen — Subagent-Output diskutieren |

## Real-world impact (12.06.2026)

Phase-B+C+D-Session: Sonnet-Subagent fand C1 + I1 + I2.

**Ohne Skill**: 3 direkt-fixes per Edit, kein Regression-Test, kein Bug-Pattern-Doku.

**Mit Skill** (heute angewandt):
- 4 neue RED-Tests in `test_v3_combo_order.py` (C1 + I1 + Edge-Case)
- RED-Phase verifiziert: alle 4 fail gegen Production-Code
- GREEN-Implementation in Commit `b634bb8`
- Test-Suite 13/13 (war 9 vor Fix) — Regression-Schutz gegen Re-Introduction

Counterfactual: bei Refactoring später wäre der Knockout-Render-Trap (C1) leicht wieder reinrutschen ohne den `test_sl_knocked_out_renders_warning_not_zero_eur`-Test.

## Cross-References

- `superpowers:requesting-code-review` — Vorgänger-Step (Review-Dispatch)
- `superpowers:receiving-code-review` — verwandt für User-Review-Feedback
- `superpowers:test-driven-development` — die TDD-Disziplin im RED→GREEN-Zyklus
- `code-review-chunk-dispatch` — für große Review-Backlogs

## Background

Pattern formalisiert 12.06.2026 nach Phase-B+C+D-Review-Cycle. Verstärkt Wolf-Maxime „Code-Review als Standard" (26.05.) um den **systematischen-Test-Aspekt** — Review-Findings sind Tests-in-Verkleidung.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill): Direct-Edit + Spot-Check, ~45min. Self-Reflection erkannte die Risiken (kein Regression-Test, Bug-Klassen unbedeckt, „done" ist Behauptung statt Beweis) — aber Default war Direct-Edit.
- **GREEN-Subagent** (mit Skill): 4 bug-pattern-Tests (test_sl_knocked_out_renders_warning_not_zero_eur, test_sl_above_ko_ask_rejected_no_positive_pnl, test_sl_equals_ko_ask_rejected, test_quantity_fallback_raises_not_silently_defaults_to_100) + RED-Verify-Pflicht. Bonus: GREEN ergänzte Edge-Case-Test (sl == ko_ask) den Skill nicht explizit verlangt. ~31min total (+19min vs RED für Regression-Schutz).
- **Refactor**: keiner blocker.

### Cycle-2-Backlog (Polish, nicht-blocking)

- **Decision-Tree „RED-Test passt unexpected"**: wenn Test gegen Production-Code passt statt zu failen, lese Production-Code → Test-Assertion verschärfen, sonst Subagent-Re-Dispatch zur Finding-Klärung
- **Finding-Cluster-Heuristik**: wenn C1 + I1 im selben Datei-Abschnitt sitzen → zusammen-Commit, sonst getrennt. Decision-Heuristik dokumentieren.
