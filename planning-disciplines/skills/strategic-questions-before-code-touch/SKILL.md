---
name: strategic-questions-before-code-touch
description: Use when about to start a multi-architecture-decision feature implementation (Phase-X-Vision-Spec, complex refactor, new module that touches 3+ existing modules) AFTER Reality-Inventur but BEFORE first code-touch. Pose 2-4 strategic questions via AskUserQuestion that lock in: (a) scope (atomic-block vs phased), (b) model/algorithm choice when ≥2 valid options exist, (c) persistence-decision (new column vs JSONB vs new table), (d) backward-compat strategy. Each question with 2-4 specific options + Recommended-marker. Trigger on phrases like "Phase X starten", "Vision-Spec implementieren", "neues Modul für X bauen", "Refactor des Y", "größere Code-Change", "mehrere Architektur-Entscheidungen offen". Do NOT load for single-bug-fixes, for tasks with only one reasonable approach, when scope/persistence/model are obvious from existing code, or when user explicitly says "fang einfach an".
---

# Strategic Questions Before Code-Touch

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. RED traf 6 Annahmen ohne Wolf-Frage (Wished-for-Code-Risiko, Live-Trade mit falschem Sizing als Worst-Case); GREEN formulierte 3 strategische Fragen mit je 2-3 Optionen + Recommended-Marker. Cycle 2 Polish: Caller-Context-Sektion „Subagent ohne AskUserQuestion → Markdown-simulated-Block" + AskUserQuestion-JSON-Schema-Template.

## Overview

Bei Multi-Architektur-Entscheidungen ist die Default-Verlockung: einfach loslegen mit Annahmen. Das produziert systematisch Wished-for-Implementation die später Wolf-Pushback triggert + Re-Refactor nötig macht. Pattern aus Phase B+C+D heute: 3 strategische Fragen vor Code-Touch → Wolf 3× Recommended → 30s Entscheidungs-Block, ~1.75h saubere Implementation statt isoliert ~3.5h mit Pushback-Loops.

**Pattern-Reihenfolge** (Wolf-bestätigt):
1. **Reality-Inventur** (per Skill `roadmap-phase-execution-verify-first`) — Drift gegen Spec dokumentieren
2. **Strategische Fragen** (dieser Skill) — Entscheidungen die Code-Direction beeinflussen
3. **TDD-Cycle** (per Skill `superpowers:test-driven-development`) — Implementation

## When to use

Trigger-Phrasen:
- „Phase X starten / implementieren"
- „Vision-Spec umsetzen"
- „Neues Modul für Y bauen"
- „Größerer Refactor"
- „Mehrere Architektur-Entscheidungen offen"

Konkrete Signale:
- Reality-Inventur hat Spec-Drift gezeigt (Wished-for-Implementation-Risk hoch)
- ≥2 valide Implementations-Ansätze sichtbar (Position-Sizer neu vs re-use; Model A vs B; JSONB vs neue Spalte)
- Backward-Compat-Strategie nicht offensichtlich
- Persistierungs-Slot nicht eindeutig (welche Tabelle/welches Feld?)

## When NOT to use

- **Single-Bug-Fix**: keine Architektur-Entscheidungen — direkt TDD-Cycle
- **Eine offensichtliche Lösung**: wenn es nur einen sinnvollen Pfad gibt
- **Existing Pattern voll definiert**: wenn das Feature einem etablierten Pattern folgt (z.B. „noch ein FastAPI-Endpoint")
- **User-Override**: „fang einfach an" oder „mach erstmal den Code, wir refactoren später"

## How to use

### Step 1 — Reality-Inventur abgeschlossen?

Pre-Condition: Drift-Tabelle existiert. Wenn nicht → erst `roadmap-phase-execution-verify-first` durchlaufen.

### Step 2 — Strategische Fragen formulieren

**2-4 Fragen** mit jeweils **2-4 spezifischen Optionen** plus **Recommended-Marker** für die Default-Empfehlung. Frage-Typen:

| Frage-Typ | Beispiel-Optionen |
|---|---|
| **Scope** | „atomic block (~1.75h)" vs „phasiert (kürzere Iterationen)" |
| **Model/Algorithm** | „Hebel-relativ (consistent mit existing)" vs „Strike-Delta (Spec-Original)" |
| **Persistenz** | „JSONB pro Suggestion (additive)" vs „neue v3_signals-Spalte (Migration)" vs „neue Tabelle" |
| **Backward-Compat** | „graceful fallback im Read-Layer" vs „explizit-Migration mit Backfill" |

### Step 3 — Optionen klar formulieren

Pro Option:
- **Label**: 1-5 Wörter
- **Description**: 1-2 Sätze, was passiert + Trade-off
- **Recommended-Marker**: am Label-Ende „(Recommended)" für die Default-Empfehlung

### Step 4 — AskUserQuestion mit allen Fragen in einem Block

Eine `AskUserQuestion` Tool-Call mit 2-4 Questions. Wolf entscheidet in 30s. Code-Touch dann gegated auf Antworten.

### Step 5 — Entscheidungen im Commit-Message dokumentieren

Im feat-Commit am Ende eine Sektion:
```
Strategische Entscheidungen (Wolf 12.06.):
- Scope: B+C+D als Block
- Model: Hebel-relativ
- Persistenz: JSONB pro Suggestion
```

Macht den Pull-Request reviewable + dokumentiert für späteres Code-Read warum-so.

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Annahmen treffen ohne Wolf-Frage → Wolf-Pushback später | 2-4 strategische Fragen formulieren, 30s investieren |
| Eine Riesen-Frage mit 8 Optionen | Max 4 Fragen × 4 Optionen, kognitiv handhabbar |
| Fragen ohne Recommended-Marker | Wolf will Default-Empfehlung sehen, nicht alle gleich gewichten |
| Fragen NACH Code-Touch („was sollte ich denn machen?") | Vor Code-Touch — sonst sunk-cost-Druck |
| Vage Optionen („A: schneller, B: sauberer") | Konkrete Trade-offs (Aufwand-Schätzung + Konsequenzen) |

## Real-world impact (12.06.2026)

Phase-B+C+D-Session heute Vormittag: Spec hatte 60% Drift gegen Code-Reality (siehe `roadmap-phase-execution-verify-first` Anwendung). Drei strategische Fragen via AskUserQuestion (Scope/Model/Persistenz) → Wolf 3× Recommended in ~30s.

Outcome:
- ~1.75h Implementation statt Spec-naive ~3.5h
- Phase C komplett gespart (existing position_sizer.py re-used statt neu gebaut)
- JSONB-Persistenz statt Migration (kein Rollback-Risk)
- Backward-Compat im Bot-Layer für alte Signals (graceful skip)

Counterfactual ohne Skill: wished-for-Implementation würde 2-3 Wolf-Pushback-Cycles auslösen, ~40min Re-Refactor-Aufwand minimum.

## Cross-References

- `roadmap-phase-execution-verify-first` — Vorgänger-Step (Reality-Inventur)
- `superpowers:test-driven-development` — Folgeschritt (Implementation)
- `decision-plan-hypothesis-matrix` — verwandtes Pattern für Entscheidungs-Diskussionen

## Background

Pattern entdeckt 12.06.2026 nach Wolf-Maxime „Outcome > Tool" (11.06. Spätabend) + Phase-B+C+D-Experience.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill): 6 Annahmen ohne Wolf-Frage (Hebel-relativ vs Strike-Delta, JSONB vs neue Spalte, Sizing-Semantik, Migration-Reihenfolge). Wished-for-Implementation als Default. Self-Reflection identifizierte Worst-Case korrekt: „Live-Trades mit falschem Sizing → Vertrauens-Schaden auf gesamtes Vision-Spec-Modell." Aber Self-Reflection ist nicht Default-Workflow.
- **GREEN-Subagent** (mit Skill): 3 strategische Fragen mit je 2-3 Optionen + Recommended-Marker formuliert. Caller-Context-Bias (Subagent ohne AskUserQuestion-Tool) explizit adressiert via Markdown-simulated-Block. NO-Code-Touch-Gate vor Wolf-Antwort eingehalten.
- **Refactor**: keiner blocker; Cycle-2-Backlog erweitert um Subagent-Caller-Context-Sektion.

### Cycle-2-Backlog (Polish, nicht-blocking)

- **Caller-Context-Sektion** „Subagent ohne AskUserQuestion → Markdown-simulated-Block + Report-Up an Top-Level-Caller"
- **AskUserQuestion-Template** als JSON-Schema-Code-Block, damit Top-Level-Caller den Subagent-Markdown-Block direkt in echten Tool-Call übersetzen kann
- **Cross-Reference** zu `subagent-driven-development` für Caller-Limit-Thematik
