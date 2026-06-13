---
name: forensik-hypothese-widerlegt-code-read-weiter
description: Use when conducting a forensic investigation with explicit hypotheses (H1/H2/H3) on a system bug or anomaly, and 2+ hypotheses have been disproved by code-read or DB-query. Default-behavior is "Hypothesis disproved → investigation done, no real bug". This skill says: continue code-read with no specific hypothesis — bonus-findings often surface during the disproving process and are real bugs that would be missed otherwise. Trigger on phrases like "Hypothese H1 widerlegt", "alle Theorien falsch", "Forensik ergebnislos", "kein Bug gefunden aber komisches Verhalten", "forensik abbrechen", "doch nichts da". Do NOT load for hypothesis-testing in research code where "disproved" is success, for time-boxed forensik with hard stop after X minutes, when user explicitly says "wenn die Hypothesen widerlegt sind, sind wir fertig", or for non-investigative tasks.
---

# Forensik: Hypothese-widerlegt → Code-Read weiter

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. GREEN strukturierte Bonus-Findings systematisch (4 Findings mit Schwere-Tabelle: 2 Critical + 1 Important + 1 Minor) — RED kam zwar selbst auf „weiter-investigieren" via Self-Reflection, lieferte aber unstrukturierte Pfad-Liste. Skill-Wert: strukturiertes Pattern statt ad-hoc-Forensik. Cycle 2 Polish: „mindestens X"-Pre-existing-Dauer-Hint, Wolf-Bestätigung-vor-DB-DELETE Cross-Ref, v3_trades-CLAUDE.md-Verlinkung.

## Overview

Forensik-Sessions starten oft mit 2-3 plausiblen Hypothesen. Default-Workflow:
1. Hypothesen formulieren
2. Pro Hypothese Evidence sammeln (Code-Read, DB-Query, Log-Inspect)
3. Wenn alle widerlegt: „Kein Bug, falsche Hypothese" → Session beenden

**Problem**: das Sammeln von Evidence führt Claude tief in den Code, der unter-untersucht war. **Bonus-Findings entstehen genau dann** — Bugs die mit der ursprünglichen Hypothese nichts zu tun haben, aber während Code-Read sichtbar werden. Default-Workflow übersieht sie.

**Fix**: nach Hypothesen-Widerlegung NICHT abbrechen. Stattdessen:
- Code-Read fortsetzen ohne spezifische Hypothese
- Auf „Anomalien zweiter Ordnung" achten (komisches Schema, redundante Code-Pfade, fehlende Constraints)
- Bonus-Findings dokumentieren mit klarer Schwere-Bewertung (Critical/Important/Minor)

## When to use

Trigger-Phrasen:
- „Hypothese H1 widerlegt"
- „Alle Theorien sind falsch"
- „Forensik ergebnislos, kein Bug"
- „Komisches Verhalten, aber keine klare Ursache"
- „Sollen wir die Forensik abbrechen?"

Konkrete Signale:
- 2+ Hypothesen wurden mit harten Evidenzen widerlegt (Code-Read zeigt Pattern nicht, DB hat erwartete Werte)
- User-Maxime: „diese Anomalie verstehe ich nicht" → Pattern für Bonus-Finding-Risk
- Code-Read war für die Hypothesen-Tests bereits 30+ Minuten investiert

## When NOT to use

- **Research-Code**: „Hypothese widerlegt" ist Success-State, nicht Bug-Hint
- **Time-Boxed Forensik**: User sagt explicit „max 30min, dann egal"
- **Eindeutiges Hypothese-Set**: wenn die 3 Hypothesen vollständig den Solution-Space abdecken
- **User-Override**: „wenn nichts gefunden wird, sind wir fertig"

## How to use

### Step 1 — Widerlegung dokumentieren

Pro widerlegter Hypothese:
- **H1**: Behauptung
- **Test**: was wurde geprüft (Code-Read/DB-Query/Log)
- **Result**: was wurde gefunden (Pattern existiert nicht / Werte ok / Logs sauber)

Diese Dokumentation bleibt im Forensik-Report — auch wenn Bonus-Findings dominieren.

### Step 2 — Code-Read-Fortsetzung ohne Hypothese

Continue mit den **angrenzenden Code-Pfaden**:
- Was passiert nach dem Test-Punkt?
- Welche **Constraints** existieren (DB-Indexes, NOT NULL, FK-Cascades)?
- Welche **silent failures** könnten passieren (try/except, COALESCE, default-values)?
- Welche **redundante Pfade** existieren (zwei Module die ähnliches machen)?

### Step 3 — Anomalien zweiter Ordnung aufspüren

Bonus-Finding-Indikatoren während Code-Read:
- „Hier sollte ein Dedup-Check sein, aber ist nicht"
- „Diese Spalte ist nullable obwohl sie required sein müsste"
- „Zwei Stages schreiben in dieselbe Tabelle ohne Coordination"
- „COALESCE versteckt NULL-Werte die als 0 gerendert werden"
- „Schema-Drift zwischen Code-Convention und DB-Reality"

### Step 4 — Bonus-Findings mit Schwere-Bewertung dokumentieren

Pro Bonus-Finding:
- **Schwere**: Critical (Geld-Verlust-Risk) / Important (User-Spam) / Minor (Cycle-2)
- **Wolf-Impact**: konkret was Wolf erlebt
- **Fix-Ansatz**: kurz skizziert
- **Pre-existing-Dauer**: wie lange war der Bug schon latent?

### Step 5 — Forensik-Report schreiben

Struktur:
1. Hypothesen-Widerlegung (kurz, evidence-basiert)
2. **Bonus-Findings** (Hauptergebnis, mit Schwere-Liste)
3. Backlog-Items + Sequencing-Empfehlung

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| „H1+H2+H3 widerlegt → Session done" | Code-Read fortsetzen mit „Anomalien zweiter Ordnung"-Auge |
| Bonus-Finding als „Random Stuff" abtun | Schwere-Bewertung + Wolf-Impact dokumentieren |
| Hypothesen-Widerlegung im Report verstecken (nur Bonus-Finding zeigen) | Beide dokumentieren — Widerlegung schützt vor späteren „warum hast du das nicht geprüft" |
| Code-Read auf einzelne Funktion beschränken | Erweitern auf Aufruf-Kette + Schema + Constraints |

## Real-world impact (12.06.2026)

Direction-Flip-vor-Advisor-Forensik:
- H1: Advisor-Cache-Lag → **widerlegt** (Code-Read: Advisor läuft async nach Persist)
- H2: Andere Datenbasis → **widerlegt** (selbe DB-Queries)
- H3: Unabhängige Direction-Berechnung im Advisor → **widerlegt** (Advisor ist Plausibility-Check, keine Direction)

Default-Workflow hätte: „Wolfs Befund ist erwartetes Verhalten, keine Action."

Mit diesem Skill: Code-Read fortgesetzt → fand `persist_signal` ohne Dedup-Check → 19 Duplikat-Cluster mit max 12-fach → **Critical-Bug-Discovery**.

Konsequenz: 4 zusätzliche Commits heute (Code-Fix + Cleanup + UNIQUE INDEX), 58 Duplikate gelöscht, künftige Telegram-Spam eliminiert.

## Cross-References

- `reporting-artefact-detection-before-claiming-anomaly` — Vorgänger-Skill (Triage vor Forensik-Start)
- `superpowers:systematic-debugging` — verwandtes Pattern für Bug-Hunt
- `db-telemetry-primary-docker-logs-secondary` — Forensik-Quellen-Hierarchie

## Background

Pattern entdeckt 12.06.2026 nach Wolf-Direktive Forensik-Direction-Flip. Ergänzt Wolf-Maxime „Erst Logs/Code/DB lesen bevor Hypothese formulieren" (25.05.) um den After-Hypothese-Continuation-Aspekt.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS — mit Caveat)

- **RED-Subagent** (ohne Skill): identifizierte selbst, dass „Alle MEINE Hypothesen widerlegt = Hypothesen-Set war unvollständig" — ist überraschend stark. Lieferte aber unstrukturierte Pfad-Liste (Telegram-Layer, Retry-Pattern, DB-Trigger, Multiple-Senders) als „möglicherweise übersehen", kein systematisches Vorgehen.
- **GREEN-Subagent** (mit Skill): strukturiertes 5-Step-Vorgehen (Widerlegung dokumentieren → Code-Read fortsetzen → Anomalien zweiter Ordnung → Bonus-Findings mit Schwere → Report). Lieferte 4 Bonus-Findings mit Schwere-Tabelle (Critical/Important/Minor) + Sequencing-Empfehlung an Wolf.
- **Skill-Wert**: RED ist „glücklicher Engineer mit Self-Awareness", GREEN ist „strukturierter Forensik-Prozess". Skill ersetzt Glück durch System.
- **Refactor**: keiner blocker.

### Cycle-2-Backlog (Polish, nicht-blocking)

- **„Mindestens X"-Pre-existing-Dauer-Hint**: wenn DB-Retention < vermutete Bug-Dauer, „mindestens X Tage, vermutlich länger" als valide Antwort dokumentieren
- **Wolf-Bestätigung-vor-DB-DELETE** Pattern als Cross-Reference (v3_trades-CLAUDE.md-Maxime)
- **Cross-Reference** auf vault-spezifische Maxime für Critical-Findings mit DB-Cleanup-Anforderung
