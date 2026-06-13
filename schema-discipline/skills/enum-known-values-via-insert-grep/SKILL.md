---
name: enum-known-values-via-insert-grep
description: Use BEFORE writing or editing a Python-side constants/enum/validator-set that should match a DB-column's real value-space — `_KNOWN_X = {...}`, `VALID_<DIMENSION> = frozenset(...)`, `class XStatus(str, Enum)`, `pydantic.Field(..., regex='^(a|b|c)$')`, in-app filter-allow-lists. STOP and grep ALL `INSERT INTO <table>` + ALL `<table>.<column> = ...` setter-lines + ALL UPDATE-statements that touch the column, BEFORE deciding the value-set in Python. Specifically trigger when (a) you write phrases like „die _KNOWN_SOURCES-Liste pflegen", „valid_phase_set definieren", „pydantic-Validator für <column> bauen", „Filter-Allowlist für UI", „neue Constants für <DIMENSION>", (b) you are about to copy a value-set from spec / docs / memory without grepping the real INSERTs first, (c) the column is shared between MULTIPLE call-sites (different services, different scripts, replay vs live, mock vs production). Also use when reviewing existing constants and the symptom is „Wert X wird silent akzeptiert" oder „Wert Y wird fälschlich rejected — er ist aber im Code". Wolf-Erlebnis 09.06.2026 Phase-5-Re-Review: `_KNOWN_SOURCES` mischte `system_phase.mode` mit `virtual_trades.source` (verschiedene Spalten verschiedener Tabellen!), Tippfehler `shadow` silent akzeptiert, echte values `manual` + `replay` fälschlich gewarnt. Method: `grep -rn "INSERT INTO <table>"` + `grep -rn "<table_var>\.<column>\s*="` + `grep -rn "UPDATE <table> SET <column>"` — dann tatsächliche Werte verifizieren + Tabelle/Spalte/Mode-Field disambiguieren (mehrere Tabellen können gleichnamige Spalten haben mit unterschiedlichen Werteräumen). Do NOT load for greenfield-tables (kein INSERT existiert, du DEFINIERST gerade), for typed-Postgres-ENUMs (PG `CREATE TYPE ... AS ENUM` zeigt die Liste in `\d` schon vollständig), oder für rein interne Python-Constants ohne DB-Bezug (z.B. UI-Theme-Names). Complement to `enum-value-discovery-before-sql-where` (this skill is for the WRITE/DEFINE side, that skill is for the SQL WHERE-read side) + complement to `schema-verify-via-information-schema` (this assumes you already know the table+column, want to know the values).
---

# Enum Known-Values via INSERT-Grep

> ✅ **PROMOTED 2026-06-10** — TDD Cycle 1 **STRONG PASS**. RED-Subagent reagierte heuristisch korrekt („erst grep") aber ohne konkrete Verifikation am echten Repo (7 Self-Critique-Punkte). GREEN-Subagent führte **18 Bash-Tool-Uses** durch im echten ultimative-platform-Repo und lieferte substantielle Befunde die ohne Skill nicht erreicht worden wären: (1) aktueller `_KNOWN_SOURCES` ist bereits anders als im Scenario angenommen (Hotfix 10.06.), (2) fehlender produktiver Wert `'real'` aus `ml/real_trade_bridge.py:142` — würde wochenlang silent `unknown source: real`-Warnings triggern, (3) Cross-Table-False-Positives explizit zurückgewiesen (`'optimizer'`, `'manual'@strategy_params`, `'av_earnings'`), (4) `_MODE_TO_SOURCES`-Mapping + DB-Constraint-Implikationen identifiziert. **R1-Refactor angewendet**: Step 4b „DB-Constraint-Verify" als eigene Sub-Sektion ergänzt — bei CHECK-Constraint / PG-ENUM begrenzt DB den Wertraum und Constants-Edit allein ist wirkungslos.

## Overview

**Eine Python-Konstanten-Liste die DB-Werte abdeckt muss aus den DB-Werten abgeleitet sein, nicht aus dem Kopf.**

Wenn du `_KNOWN_X = {...}`, `VALID_<DIMENSION>`, `pydantic.Field(regex="^(a|b|c)$")`, oder einen Status-Enum-Validator schreibst, ist das ein **Vertrag mit der Datenbank**. Wenn die Liste vom echten Wertraum abweicht:

- **Falsch-positiv**: Tippfehler-Werte rutschen durch („shadow" wird akzeptiert obwohl niemand das insertet)
- **Falsch-negativ**: echte Werte werden gewarnt / abgelehnt („manual" wird `unknown source`-warning obwohl es legitim ist)
- **Cross-Table-Drift**: Spalten gleichen Namens existieren in mehreren Tabellen mit unterschiedlichen Werteräumen — Python-Side mischt sie versehentlich

Skill = Disziplin: **`grep -rn "INSERT INTO <table>"` + alle `<column> =`-Setter BEVOR die Konstante geschrieben wird.**

Diese Maxime ist die Definition-Side-Variante der Wolf-Maxime „Schema-Drift vermeiden" (08.06.2026 CLAUDE.md): nicht nur die Spalten existieren-müssen, sondern auch die Wert-Räume müssen mit der Code-Side abgleichen.

## When to use

**Trigger-Phrasen (du würdest gerade sagen)**:
- „die _KNOWN_X-Liste pflegen / erweitern"
- „valid_phase_set / valid_states definieren"
- „pydantic-Validator für die <column> bauen"
- „Filter-Allowlist für UI / API"
- „neue Constants für DIMENSION X"
- „Enum-Class für <column> schreiben"
- „Allowed-Values für <field>"

**Symptom-Trigger** (du untersuchst einen bestehenden Skill):
- „Wert X wird silent akzeptiert obwohl niemand X insertet" → grep INSERTs
- „Wert Y wird `unknown source`-warning, ist aber im Code als Setter da" → grep INSERTs + Setters
- „Cohort A vs B aus DB" → check ob beide Cohorts gleiches Werte-Vokabular nutzen

**Hochrisiko-Marker**:
- Die Spalte hat **gleichen Namen in mehreren Tabellen** (z.B. `mode` in `system_phase` UND `virtual_trades` UND `signals_log`)
- Die Spalte ist **type `text`** statt `enum` — PG hilft nicht
- Die Werte werden in Python-Code an **mehreren Stellen geschrieben** (mehrere Services, mehrere Worker)
- Code hat eine `_KNOWN_X`-Set ODER eine Pydantic-Validator ODER ein UI-Dropdown auf die gleiche Spalte
- Replay-Mock-Setter unterscheidet sich vom Live-Setter

## When NOT to use

- **Greenfield-Tabelle**: kein INSERT existiert, du **definierst** die Werte gerade. Dann Constants → Migration → Setter, in dieser Reihenfolge
- **Typed PostgreSQL ENUM** (`CREATE TYPE foo AS ENUM ('a', 'b', 'c')`): `\d <table>` zeigt die Liste vollständig + DB lehnt unknown values bereits ab
- **Rein interne Python-Constants** ohne DB-Bezug (UI-Theme-Names, in-memory Cache-Keys)
- **Single-Writer-Pattern** mit Code-Lock (nur eine Klasse darf inserten + sie nutzt die Constants-Liste — Validators are co-located)

## The 4-Step Insert-Grep Flow

### Step 1 — Tabelle + Spalte explizit identifizieren

Vor dem grep festhalten:
- **Tabelle**: z.B. `virtual_trades`
- **Spalte**: z.B. `source`
- **Vermutete Werte-Liste**: z.B. `{"live", "training", "shadow"}`
- **Annahme über Disambiguierung**: gibt es **gleichnamige Spalten in anderen Tabellen**? (Risiko-Check)

### Step 2 — Drei Grep-Pässe für INSERTs + Setters + UPDATEs

```bash
# Pass 1: INSERT-statements (alle INSERTs touching virtual_trades)
grep -rn "INSERT INTO virtual_trades" --include="*.py" | head -50

# Pass 2: Setter-lines (column = value oder dict-Schreibweise)
grep -rn "\.source\s*=\s*['\"]" --include="*.py" \
  | grep -E "(virtual_trade|vt|trade)" \
  | head -50

# Pass 3: UPDATE-statements
grep -rn "UPDATE virtual_trades SET" --include="*.py" | grep "source"

# Pass 4 (Cross-Table-Check): same column-name in other tables
grep -rn "['\"]source['\"]" --include="*.sql" | head -20
grep -rn "\.source\s*=" --include="*.py" | head -20  # ohne table-filter
```

### Step 3 — Wert-Set aus Treffern destillieren

Sortiere jeden Treffer:

| Wert | Quelle | Wirklich genutzt? | Ähnlich-aber-anders? |
|---|---|---|---|
| `'live'` | `services/live_dispatcher.py:42` | ✅ ja | — |
| `'training'` | `services/training_runner.py:104` | ✅ ja | — |
| `'manual'` | `cli/manual_trade.py:67` | ✅ ja | — |
| `'replay'` | `scripts/replay_session.py:88` | ✅ ja | — |
| `'shadow'` | `services/system_phase.py:21` (setzt `system_phase.mode`!) | ❌ falsche Tabelle | gehört zu `system_phase.mode`, nicht zu `virtual_trades.source` |

### Step 4 — Konstanten korrekt definieren mit Cross-Table-Disambiguierung

```python
# WRONG (mischt zwei Tabellen):
_KNOWN_SOURCES = {"live", "training", "shadow"}  # 'shadow' gehört nicht hierher

# RIGHT (eine pro Tabelle/Spalte, dokumentiert):
# virtual_trades.source — values from INSERT-grep 2026-06-10
_KNOWN_TRADE_SOURCES = {"live", "training", "manual", "replay"}

# system_phase.mode — separate Set
_KNOWN_PHASE_MODES = {"live", "training", "shadow"}
```

Im Validator oder Logger-Warning:
- Verwende `_KNOWN_TRADE_SOURCES` für `virtual_trades.source`
- Verwende `_KNOWN_PHASE_MODES` für `system_phase.mode`
- Nicht mischen, niemals

### Step 4b — DB-Constraint-Verify (R1-Refactor 10.06.2026)

**Wenn die Spalte in der DB durch einen `CHECK`-Constraint, eine PG-`ENUM`-Typ-Definition, oder eine Foreign-Key-Lookup-Tabelle den Wertraum begrenzt, ist der Constants-Edit allein wirkungslos** — neue Werte werden vom DB-Engine zurückgewiesen mit `CheckViolation` oder `InvalidTextRepresentation`.

```bash
# CHECK-Constraint auf der Spalte?
psql -c "\d+ virtual_trades" | grep -A1 "Check constraints"

# Wenn ENUM-Typ:
psql -c "\dT+ source_type"  # zeigt die enum-Werte

# Wenn FK-Lookup:
psql -c "SELECT * FROM source_lookup;"
```

**Bei begrenzendem DB-Constraint**: braucht zusätzliche Migration **VOR** dem Python-Constants-Edit:

```sql
-- Beispiel CHECK-Constraint erweitern
ALTER TABLE virtual_trades DROP CONSTRAINT IF EXISTS virtual_trades_source_check;
ALTER TABLE virtual_trades ADD CONSTRAINT virtual_trades_source_check
  CHECK (source IN ('live', 'training', 'manual', 'replay', 'real', 'paper'));

-- Beispiel PG-ENUM erweitern (PG13+)
ALTER TYPE source_type ADD VALUE 'paper';
```

Reihenfolge: **DB-Migration → Python-Constants-Update → Setter-Code → Test**. Umgekehrt kracht's beim ersten echten INSERT.

## Quick Reference

| Constants-Typ | Grep-Pattern (Beispiel) |
|---|---|
| `_KNOWN_X = {...}` | `grep -rn "INSERT INTO <table>" + grep -rn "\.<col>\s*="` |
| `pydantic regex='^(a|b)$'` | gleiches plus `grep "<col>:.*=" --include="*.py"` |
| `class XEnum(str, Enum)` | gleiches plus `grep "class.*Enum"` für existierende Enums |
| UI-Dropdown-Options | gleiches plus `grep "options=\[" --include="*.ts,*.py"` |

## Anti-Patterns

| Anti-Pattern | Lehre |
|---|---|
| `_KNOWN_X` aus Spec/Doku übernehmen ohne grep | Spec wird drift, Code nicht — Single Source of Truth ist INSERT |
| „Ich kenne die 3 Werte aus dem Kopf" | Wolf 09.06.: 3 von 5 Werten lagen daneben (Tippfehler `shadow` + fehlende `manual`/`replay`) |
| Spalten-Name als Disambiguierung ausreichend | `mode` existiert in `system_phase` UND `signals_log` UND `virtual_trades` — gleich-Name ≠ gleich-Werteraum |
| Validators ohne Tabellen-Suffix | `_KNOWN_SOURCES` mehrdeutig; `_KNOWN_TRADE_SOURCES` + `_KNOWN_PHASE_MODES` explizit |
| Werte-Liste in einer einzelnen Datei statt zentral | Jede neue Source landet bei nur einem Maintainer → drift garantiert. **Ein** Validators-Modul pro DB-Spalte |

## Cost of Skipping (real)

**Wolf-Erlebnis 09.06.2026 Phase-5-Re-Review** (Schema-Drift-Sweep):
- `_KNOWN_SOURCES = {"live", "training", "shadow"}` aus Erinnerung
- Reality (durch INSERT-grep aufgeklärt): `virtual_trades.source` hatte tatsächlich `{"live", "training", "manual", "replay"}` (keine `shadow`)
- `shadow` war eine `system_phase.mode`-Wert — andere Tabelle
- Konsequenz vor Fix: `manual` + `replay` lösten silent `unknown source`-warnings aus (Logs zugefüllt), `shadow`-Tippfehler hätte fälschlich akzeptiert
- Fix: zwei getrennte Constants-Sets pro Tabelle

**Pattern**: gleichnamige Spalten in verschiedenen Tabellen mit unterschiedlichen Wertebereichen sind eine der häufigsten Drift-Quellen. Python-Side nicht aus dem Kopf — aus dem INSERT.

## Red Flags — STOP and grep

- Du schreibst gerade `_KNOWN_<DIMENSION>` oder einen Pydantic-Validator
- Deine Werte-Liste kommt aus dem Kopf / aus Spec / aus alter Doku
- Die Spalte könnte in mehreren Tabellen existieren
- Du hast keine Validators-Convention pro Tabelle/Spalte etabliert

**Alle bedeuten: 3 Grep-Pässe (INSERT, Setter, UPDATE) + Cross-Table-Check, dann Constants pro Tabelle/Spalte explizit benennen.**

## Cross-References

- **COMPLEMENT (Lese-Seite)**: `enum-value-discovery-before-sql-where` — gleicher Schmerz aus SQL-WHERE-Sicht
- **COMPLEMENT**: `schema-verify-via-information-schema` — verifiziert dass die Spalte überhaupt existiert
- **COMPLEMENT**: `silent-except-versteckt-schema-drift` — der `except Exception: x = []`-Pattern versteckt diese Drift-Bugs
- Wolf-Maxime: „Single Source of Truth — Hardcoded-Defaults sind tickende Bomben" (`CLAUDE.md` Vault, 09.06.2026)

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-10 (STRONG PASS mit R1-Refactor)

- **RED-Subagent** (ohne Skill, Scenario „Erweitere _KNOWN_SOURCES um 'paper' für Paper-Trading-Mode"): Reagierte heuristisch korrekt aus CLAUDE.md-Pattern („erst grep"), aber **ohne Repo-Zugriff** — gab Befehle vor statt sie auszuführen. Self-Critique listete 7 Punkte (keine konkrete Verifikation, Migrations-Geschichte ignoriert, Test-Fixtures nicht erwähnt, Logging-Downstream übersehen, Naming-Konvention nicht geprüft, Wolf-spezifische Notizen nicht durchsucht, Frage „reicht das?" nicht direkt beantwortet).

- **GREEN-Subagent** (mit Skill): **Führte 18 Bash-Tool-Uses durch** im echten Production-Repo `~/Documents/Claude-Code/ultimative-platform/` und lieferte 4 substantielle Befunde:
  1. **Code-Stand-Drift**: `_KNOWN_SOURCES` ist im aktuellen Code bereits `{"training", "live", "backtest", "manual", "replay"}` — NICHT die im Scenario behauptete Liste. Hotfix vom 10.06. Phase-5-Re-Review war bereits geschehen.
  2. **Bestandsschuld entdeckt**: `ml/real_trade_bridge.py:142` schreibt `source='real'` in `virtual_trades`, fehlt aber in `_KNOWN_SOURCES` → silent `unknown source: real`-Warnungen.
  3. **Cross-Table-False-Positives korrekt zurückgewiesen**: `'optimizer'`, `'av_earnings'`, `'combo_optimizer'` → andere Tabellen (`strategy_params.source`, etc.), gehören NICHT in `virtual_trades.source`-Set.
  4. **`_MODE_TO_SOURCES`-Mapping + DB-Constraint-Implikation**: Wenn `system_phase.mode='paper'` triggert, muss zusätzlich `_MODE_TO_SOURCES` UND ggf. PG-ENUM/CHECK-Constraint erweitert werden — sonst kracht's beim ersten `SET mode='paper'`-Versuch.

- **R1-Refactor angewendet**: Step 4b „DB-Constraint-Verify" als eigene Sub-Sektion ergänzt mit Code-Beispielen für CHECK-Constraint-Update, PG-ENUM-Extension, FK-Lookup-Insert. Reihenfolge explizit dokumentiert: DB-Migration → Python-Constants → Setter → Test.

- **Vermiedener Anti-Pattern**: GREEN nannte explizit dass die naheliegende Antwort „Ja, ergänze einfach 'paper'" 4 Bugs erzeugt hätte: (a) übersieht 10.06.-Hotfix, (b) lässt `'real'` fehlen, (c) zementiert `'shadow'`-Cross-Table-Fehler, (d) lässt DB-Constraint krachen.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Test-Pattern für Vollständigkeits-Check**: Test der `_KNOWN_X` gegen `_MODE_TO_X`-Mapping abgleicht (jeder Mode-Wert muss in Sources-Set sein). GREEN hat das vorgeschlagen.
2. **CWD-Mismatch-Hinweis** für Subagents: Repo-Pfad explizit machen wenn CWD nicht das Production-Repo ist.
3. **DB-Live-Verify als optionaler Step 4c**: `SELECT source, COUNT(*) FROM <table> GROUP BY source` für Bestands-Werte-Audit. Komplementär zu Step 2 INSERT-grep.
4. **Cross-Reference**: `schema-use-case-mismatch-detection` (gibt es?) als Komplement bei DB-Side-Wertraum-Begrenzung.
