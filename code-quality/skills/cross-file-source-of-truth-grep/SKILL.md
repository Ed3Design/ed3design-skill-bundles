---
name: cross-file-source-of-truth-grep
description: Use when you are about to refactor a value, constant, helper-function, lookup, or config-pattern from old-form to new-form across the codebase — schema-drift fixes („`yf_symbol` → `symbol`"), display-name SoT migration („inline-dict → `core/utils/display.instrument_label`"), config-pattern updates („hardcoded VRM-ID → env-var"), helper-function rename, deprecated-import-cleanup. STOP and run `grep -r "<old-pattern>"` on the WHOLE repo (not just the files you have open) BEFORE writing the new pattern anywhere. Specifically trigger when (a) you write phrases like „ich refactore X auf Y", „Schema-Drift in Y beheben", „migriere von alter auf neue Form", „rename helper", „config-Default rausziehen", „display-name single-source-of-truth", (b) you have a mental model „die 3 Files die das nutzen" or „nur in /core/ relevant" — gerade dispatcher / scheduler / jobs / notifications / tests verstecken oft 1-2 weitere Stellen, (c) the new pattern is in production code but you haven't checked notification-dispatcher, scheduler-jobs, batch-scripts, integration-tests, mock-fixtures. Wolf-Erlebnis 09.06.2026 Phase-1-Re-Review: `notifications/signal_dispatcher.py:_get_display_name` rief noch alten `config_loader`-Pfad auf, obwohl der Hauptpfad migriert war — wäre wochenlang unbemerkt im V1/V2-Signal-Telegram-Dispatch geblieben. Method: `grep -rn "<altes-pattern>" --include="*.py"` mit Ausschluss von `node_modules`, `.git`, `*.pyc`, `__pycache__`, dann jede Trefferzeile lesen + zuordnen (Production / Notification / Scheduler / Test / Mock / Deprecated). Do NOT load for greenfield-code (no old pattern to migrate from), for renames that are pure cosmetics with no semantic shift (e.g. variable in same file), for refactors that are guaranteed file-local (private helper in a single module). Complements `pre-deploy-code-drift-detection` (this skill catches drift VOR dem Refactor, that one catches drift NACH dem Refactor); complement to `silent-except-versteckt-schema-drift` (which finds the same kind of dormant bug from the symptom side).
---

# Cross-File Source-of-Truth Grep

> ✅ **PROMOTED 2026-06-10** — TDD Cycle 1 PASS. RED-Subagent gab heuristisch „erst grep" Empfehlung, aber ohne den entscheidenden 4. Grep-Pass auf Mapping-Werte. GREEN-Subagent ergänzte den 4. Pass `grep -rn "'CL=F'\s*:\s*'WTI"` — der genau Kopien der Mapping-Struktur unter abweichenden Variablen-Namen fängt (`_DISPLAY_MAP`, `LABELS`, in-Helper-Function-eingebettete Dicts). Genau dieser Pass hätte den 09.06.-`signal_dispatcher.py:_get_display_name`-Bug vor dem Refactor abgefangen. **R1-Refactor angewendet**: 4. Grep-Pass in Quick-Reference als separate Zeile + Hinweis-Block.

## Overview

**Vor jedem Refactor: grep -r auf den ALTEN Pattern, nicht auf den NEUEN.**

Wenn du ein altes Pattern (Spaltennname, Helper-Aufruf, Inline-Dict, Default-String, deprecated-Import) durch ein neues ersetzt, brennen sich häufig **2-5 zusätzliche Aufrufer** ein die du im mentalen Modell „die 3 relevanten Files" nicht hattest:

- `notifications/`-Dispatcher (Telegram, Email, Webhook)
- Scheduler-Jobs (cron-getriggert, oft wenig touched)
- Batch-Scripts (offline analytics)
- Integration-Tests + Mock-Fixtures
- Deprecated-aber-noch-im-Pfad-Module

Skill = simple Disziplin: **`grep -rn "<altes-pattern>"` BEVOR du den ersten neuen Aufruf schreibst.** 30 Sekunden Aufwand verhindern Stunden Re-Review-Cycle.

Diese Maxime ist die Refactor-Variante der Wolf-Maxime „Single Source of Truth" (09.06.2026): die SoT-Migration ist erst dann vollständig wenn der grep auf das alte Pattern leer ist.

## When to use

**Trigger-Phrasen (du würdest gerade sagen)**:
- „ich refactore <X> auf <Y>"
- „Schema-Drift in <table>.<column> beheben"
- „SoT für <Display-Name / Config-Var / Helper> einziehen"
- „migriere von altem `config_loader`-Pfad auf neuen"
- „rename helper-function von foo auf bar"
- „deprecated import cleanup"
- „die config-Defaults aus dem Code rausziehen"

**Hochrisiko-Marker** (zusätzlicher Trigger):
- Du hast im Kopf eine kleine Liste betroffener Files (≤5) — gerade dann grep, weil das ist die unterschätzungsanfällige Lage
- Das neue Pattern lebt schon irgendwo („wir haben das in `core/` standardisiert") — d.h. ältere Stellen sind noch nicht migriert
- Modul gehört zu **Notification / Dispatcher / Scheduler / Cron / Batch** — diese Pfade werden seltener touched, drift häuft sich

## When NOT to use

- **Greenfield-Code**: das alte Pattern existiert noch nicht
- **Reiner Cosmetic-Rename in einer Datei**: lokale Variable, keine semantische Verschiebung
- **Garantiert file-lokaler Helper**: `_private_helper` im Modul, mit `_`-Präfix-Konvention
- **Rename eines Symbols mit IDE-Refactor-Tool**: wenn LSP-Refactor sauber alle Aufrufer abdeckt, ist grep redundant (aber **danach** trotzdem 1× verifizieren)

## The 4-Step Cross-File-SoT-Grep Flow

### Step 1 — Altes Pattern explizit notieren

Vor dem grep schreibe als Kommentar oder TodoWrite:
- **Altes Pattern**: `o.yf_symbol` (Spalten-Alias)
- **Neues Pattern**: `o.symbol AS yf_symbol`
- **Vermutete Aufrufer-Anzahl**: 3 (`signals.py`, `timeline.py`, `take_signal`)
- **Was ich vermute zu finden**: 3-5 (mit ~2 Extra in Tests/Mocks)

### Step 2 — Grep mit Repo-Scope

```bash
# Standard: alle Python-Files inkl. tests, scripts, integrations
grep -rn "<altes-pattern>" --include="*.py" \
  --exclude-dir=node_modules \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  | grep -v "\.pyc:"
```

**Niemals** nur in einem Sub-Verzeichnis (`grep ... /core/`). Das verfehlt das Skill-Ziel.

### Step 3 — Trefferliste kategorisieren

Sortiere jeden Treffer in eine dieser Kategorien:

| Kategorie | Beispiel | Aktion |
|---|---|---|
| **Production-Hot-Path** | `core/services/X.py` | migrieren (Pflicht) |
| **Production-Cold-Path** | `notifications/dispatcher.py`, `scheduler/jobs/Y.py` | **migrieren** + Pre-Push-Hook-Live-Smoke wenn möglich |
| **Test/Mock** | `tests/integration/test_Y.py` mit fixed-Daten | migrieren + Fixture-Updates |
| **Doc / Comment / Note** | `# old: yf_symbol` | so lassen (Historie) ODER ersetzen wenn fully-replace gefordert |
| **Deprecated-aber-im-Pfad** | `legacy/foo.py` mit Import von Production | **explizit entscheiden**: migrieren ODER deprecation-Hinweis + Issue |
| **False-Positive** | substring-match in Variable-Name | ignorieren |

### Step 4 — Migrieren + Verifikations-Grep

Nach dem Refactor: **erneut `grep -rn "<altes-pattern>"`** — Ergebnis sollte leer sein (oder nur die Doc/Comment-False-Positives bleiben).

```bash
grep -rn "<altes-pattern>" --include="*.py" | wc -l
# Erwartung: 0 (oder Liste der bewusst nicht-migrierten Treffer)
```

## Quick Reference

| Refactor-Typ | Grep-Pattern (Beispiel) |
|---|---|
| Spalten-Rename | `grep -rn "\.yf_symbol\\|yf_symbol AS"` |
| Helper-Rename | `grep -rn "from .* import old_helper\\|old_helper("` |
| Inline-Dict → SoT (Variablen-Name) | `grep -rn "display_names\\s*=\\s*{"` |
| **Inline-Dict → SoT (Werte-Substring, fängt verschleierte Namen)** | **`grep -rn "'CL=F'\\s*:\\s*'WTI"` — fängt `_DISPLAY_MAP`, `LABELS`, `SYMBOL_NAMES` etc. die das gleiche Mapping unter anderem Namen kopieren** |
| Deprecated Import | `grep -rn "from config_loader import"` |
| Hardcoded Env-Default | `grep -rn '"c0619ab1e363"\\|"my-host"'` (Beispiel-Werte) |
| Magic-String → Enum | `grep -rn "'long'\\|'short'" --include="*.py"` |

> **R1-Refactor (10.06.2026 Cycle 1)**: Der Substring-Grep auf Mapping-**Werte** (`'CL=F': 'WTI`) ist die kritischste Variante — sie findet Kopien der Mapping-Struktur unter abweichendem Variablen-Namen. Genau diese Variante hätte den 09.06.-`signal_dispatcher.py:_get_display_name`-Bug VOR dem Refactor abgefangen (dort hieß das Dict nicht `display_names` sondern war eingebettet in eine Helper-Funktion).

## Anti-Patterns

| Anti-Pattern | Lehre |
|---|---|
| „Ich kenne die 3 Files die das nutzen" | Mentale Modelle übersehen Notification/Scheduler/Batch — grep ist 30s, weniger als die Re-Review-Cycle |
| Nur in `core/` greppen | Notification-Dispatcher liegt oft in `notifications/`, Scheduler-Jobs in `scheduler/jobs/` — repo-weit greppen |
| Grep ohne `--include="*.py"` | Treffer in `.pyc`, `.log`, `node_modules` rauschen Output zu |
| Nach Refactor nicht erneut greppen | Verifikations-grep ist die Schlussprüfung — leerer Output = Migration vollständig |
| LSP-Refactor blind vertrauen | LSP findet meist alles, aber Dynamic-Imports (`importlib`) und String-Schlüssel (`getattr(o, "yf_symbol")`) entgehen — grep findet beide |

## Cost of Skipping (real)

**Wolf-Erlebnis 09.06.2026 Phase-1-Re-Review** (Code-Review-Aufarbeitung):
- Display-Name-SoT-Migration nach `core/utils/display.instrument_label()` hatte 4 Hot-Path-Files gefasst
- Re-Review-Subagent fand `notifications/signal_dispatcher.py:_get_display_name` mit altem `config_loader`-Pfad
- Wäre **wochenlang unbemerkt** im V1/V2-Signal-Telegram-Dispatch geblieben — Symbole im Telegram statt Display-Names

**Pattern**: Notification-Dispatcher-Module werden seltener touched + haben oft eigene Helper-Versions die nicht im Haupt-Refactor-Pfad sichtbar sind.

**Lehre**: 30s Grep vorher = Stunden Re-Review-Cycle gespart.

## Red Flags — STOP and grep

- Du schreibst gerade den ersten neuen Aufruf nach einem Refactor
- Dein mentales Modell ist „die 3 Files" oder „nur in /core/"
- Notification/Scheduler/Batch wurden in deiner Liste **nicht** explizit erwähnt
- LSP-Refactor lief sauber, aber du hast Dynamic-Imports im Codebase

**Alle bedeuten: 30s repo-weiter Grep auf altes Pattern, dann Trefferliste kategorisieren, dann erst migrieren.**

## Cross-References

- **REQUIRED COMPLEMENT**: `pre-deploy-code-drift-detection` (Drift-Check NACH dem Refactor)
- **COMPLEMENT**: `silent-except-versteckt-schema-drift` (gleiche Bug-Klasse aus Symptom-Sicht)
- Wolf-Maxime: „Single Source of Truth — Hardcoded-Defaults sind tickende Bomben" (`CLAUDE.md` Vault, 09.06.2026)

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-10 (PASS mit R1-Refactor)

- **RED-Subagent** (ohne Skill, Scenario „display_names-Inline-Dicts auf zentrale `instrument_label()` migrieren, 3 Files bekannt"): Empfahl heuristisch „erst grep nach weiteren Vorkommen" — überraschend gut, aber **nur den Variablen-Namen-Grep** (`grep -rn "display_names"`). Self-Critique listete 7 Punkte (Repo nicht angeschaut, DB als SoT nicht thematisiert, Migration-Reihenfolge bei Imports, Tests vor Löschen, Tooling-Hinweis, Anti-Pattern-Bogen-Schlag, kein Dict-Diff vor Merge).

- **GREEN-Subagent** (mit Skill): Brachte den entscheidenden Mehrwert — den **4. Grep-Pass auf Mapping-Werte** (`grep -rn "'CL=F'\s*:\s*'WTI"`) der Kopien der Mapping-Struktur unter abweichenden Variablen-Namen fängt. Plus: konkrete Hochrisiko-Pfade für ultimative-platform-Codebase benannt (`notifications/signal_dispatcher.py`, `notifications/telegram_*.py`, `scheduler/jobs/*.py`, `briefings/*.py`), Cross-Reference auf `pre-deploy-code-drift-detection` als Komplement nach dem Refactor, Schema-Use-Case-Mismatch-Hinweis (`display_name IS NULL`-Check).

- **R1-Refactor angewendet**: Quick-Reference-Tabelle um Zeile „Inline-Dict → SoT (Werte-Substring, fängt verschleierte Namen)" erweitert + Hinweis-Block dass dies die kritischste Variante ist (hätte 09.06.-Bug abgefangen).

- **Vermiedener Anti-Pattern**: GREEN hat den 09.06.-Bug exakt vorhergesagt — `notifications/signal_dispatcher.py` mit eigenem `_get_display_name` würde unmigriert bleiben, wochenlang Roh-Symbole im V1/V2-Telegram-Dispatch.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **CWD-Hinweis** für Subagent-Use-Cases: „wenn dein CWD nicht das Ziel-Repo ist: erst `cd` oder Befehle an User delegieren". GREEN-Subagent hatte CWD-Mismatch (Vault statt Repo) und musste das durch Befehl-Vorgabe lösen.
2. **LSP find_references als Komplement-Quelle** (nicht nur als Anti-Pattern): bei LSP-fähigen Repos zusätzliche Verifikation neben grep.
3. **Schema-Use-Case-Mismatch als expliziter Sub-Check** in Step 3: bei DB-gestützten Lookups (`instruments.display_name IS NULL`) ist ein DB-Datenstand-Check vor Migration nötig — ist eigene Drift-Klasse.
4. **Hochrisiko-Pfade-Liste** für ultimative-platform-Codebase als Quick-Reference: notification/, scheduler/, briefings/, analytics/, tests/integration/ — projekt-spezifisch wertvoll.
