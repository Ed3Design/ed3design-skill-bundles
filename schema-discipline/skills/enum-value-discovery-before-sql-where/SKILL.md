---
name: enum-value-discovery-before-sql-where
description: Use BEFORE writing any SQL WHERE-clause that filters on a string/enum-typed column. Schema-verify via `\d <table>` shows COLUMN TYPE (text/varchar/enum) but NOT the actual values used. Code may set 'taken' while reviewer thinks 'accept'. Pattern: run `SELECT DISTINCT <col> FROM <table>` (or grep for `_update_<col>`-style setters in code) to discover the actual value-set BEFORE formulating WHERE. Without this discovery step, queries silently return wrong counts: rows matching the real value get excluded, user sees "0 results" while reality has many. The drift between assumed-values and actual-values is invisible in schema-introspection alone. Trigger on phrases like "wie viele <entity> mit status X gibt es", "user_response='accept'", "SELECT ... WHERE <enum_col>=...", "warum sehe ich keine Treffer", "forensische DB-Analyse", "Migration-Cleanup mit Status-Filter", "Cockpit-Filter zeigt 0", "Trade-Forensik". Do NOT load for known well-defined enum-types (PostgreSQL `CREATE TYPE ... AS ENUM`) where psql `\d` shows the value-set inline, for first-time-CREATE-TABLE queries (no existing data), or for non-text/non-enum columns (numeric/timestamp filters don't have this discovery-need).
---

# enum-value-discovery-before-sql-where

> ✅ **PROMOTED 2026-05-27**: Pattern aus Wolf-ultimative-platform 27.05.2026 Phase-2-Forensik-Session entstanden. TDD-Pressure-Test bestanden: GREEN-Subagent erkannte das 27.05.-Beispiel als 1:1-Szenario und vermied `WHERE user_response='accept'`-Anti-Pattern; RED gab dasselbe Anti-Pattern aus (war zwar selbstkritisch, hätte aber falsche Query an Wolf geliefert).

## Pattern (Kurzform)

Vor jeder SQL-WHERE-Klausel mit string-/enum-typed-Spalte:

1. **Schema-Check** (Wolf-Maxime „DB-Schema verifizieren"): `\d <table>`
   → liefert SPALTE + TYP, ABER nicht die tatsächlich verwendeten Werte
2. **Werte-Discovery**: `SELECT DISTINCT <col> FROM <table> ORDER BY 1;`
   → liefert die echten Werte. ODER alternativ: Code-Grep nach Settern (`_update_<col>`, `SET <col> = '...'`).
3. **Erst dann** WHERE-Klausel formulieren mit verifizierten Werten

Wenn (3) ohne (2) gemacht wird → Query liefert silent falsche Counts. Reviewer sieht "0 rows" wo Realität viele hat, geht in falsche Schlussfolgerungs-Spirale.

## Konkretes Beispiel (heutige Live-Begegnung 27.05.2026)

**Aufgabe**: Forensik-Baseline für ultimative-platform v3-Signal-Performance.

**Falsche Query**:
```sql
SELECT
  date_trunc('week', triggered_at)::date AS week_start,
  SUM(CASE WHEN user_response='accept' THEN 1 ELSE 0 END) AS user_accepted
FROM v3_signals
WHERE triggered_at >= NOW() - INTERVAL '4 weeks'
GROUP BY 1;
```

**Ergebnis**: `user_accepted = 0` in ALLEN Wochen.
**Schluss**: „User-Response-Loop ist broken, Wolf hat nie accepted".

**Wolf-Korrektur**: „Ich habe durchaus Signale Accepted (Alphabet, Bayer)."

**Realität via Werte-Discovery**:
```sql
SELECT user_response, COUNT(*) FROM v3_signals GROUP BY user_response;
```
```
 user_response | count
---------------+-------
 pending       |   107
 taken         |    17  ← Wolfs Accepts hier!
 skipped       |     5
```

→ Code setzt `'taken'`, nicht `'accept'`. Grep-Verify im Code:
```bash
grep -rn "user_response\s*=" --include="*.py" .
# strategic/v3_trade_manager.py:96: mark_signal_taken → 'taken'
# strategic/v3_trade_manager.py:100: mark_signal_skipped → 'skipped'
```

→ Original-Query muss zu `WHERE user_response='taken'` korrigiert werden. Realität war 17 accepts, nicht 0.

## Quick-Reference: wann discovery, wann skippen

| Situation | Discovery nötig? |
|---|---|
| WHERE auf `text`-/`varchar`-Spalte mit string-Wert | ✅ JA, immer |
| WHERE auf PostgreSQL-`ENUM`-Typ (`CREATE TYPE ... AS ENUM`) | ⚠️ Nein wenn `\d` die Werte zeigt — sonst JA |
| WHERE auf `boolean` | ❌ Nein (nur 2 Werte) |
| WHERE auf `integer` mit Range-Filter (>, <) | ❌ Nein |
| WHERE auf Timestamp/Date | ❌ Nein |
| WHERE auf `id IN (...)` mit konkreten IDs | ❌ Nein |
| JOIN-Bedingung mit string-Spalte | ✅ JA bei beiden Tabellen |
| AGGREGATE wie `SUM(CASE WHEN col='X' THEN ...)` | ✅ JA — gleiche Falle wie WHERE |

## Discovery-Methoden (in Reihenfolge der Geschwindigkeit)

### A. DB-Query (1-2s, immer korrekt)
```sql
SELECT DISTINCT <col> FROM <table> ORDER BY 1;
-- oder mit counts:
SELECT <col>, COUNT(*) FROM <table> GROUP BY <col> ORDER BY 2 DESC LIMIT 20;
```

### B. Code-Grep (5-10s, zeigt Setter-Intent)
```bash
# Wo wird die Spalte gesetzt?
grep -rn "SET <col>\s*=" --include="*.py" --include="*.sql"
grep -rn "<col>\s*=\s*['\"]" --include="*.py"
# Functions die den Wert setzen:
grep -rn "mark_<entity>\|set_<col>\|update_<col>" --include="*.py"
```

### C. Schema-Migration-Backtrace (komplex, nur bei history-Fragen)
```bash
grep -rn "<col>" core/db/migrations.py  # falls dort initialisiert
git log -p -- core/db/migrations.py | grep -A 2 "<col>"
```

→ Bei Live-Forensik: **A first**. Bei Code-Verständnis-Fragen ohne Live-DB: **B first**.

## Anti-Patterns

| Anti-Pattern | Korrekt |
|---|---|
| `WHERE status='active'` ohne Discovery | erst `SELECT DISTINCT status FROM ...` |
| „Status-Werte sind doch immer pending/accept/reject" — Annahme aus Trainingsdaten | jedes System hat eigene Konvention, verifizieren |
| Forensik-Report mit „0 rows match" als Befund präsentieren | erst Werte-Discovery, sonst falsche Schlussfolgerung |
| `\d <table>` als ausreichende Schema-Verifikation | Schema sagt nur TYP, nicht WERTE |
| Bei AGGREGATE-Funktionen die Discovery überspringen (`SUM(CASE WHEN col='X'...)`) | gleiche Falle wie WHERE — Aggregate mit falschem String returnen still 0 |
| Wolfs „funktioniert doch" gegen Daten-Ergebnis ignorieren | wenn User-Realität ≠ Daten, ist Query verdächtig — Discovery ausführen |

## Discovery-Surrogate ohne Live-DB-Zugriff

Wenn du kein Live-`psql` hast (Subagent-Context, Code-Review ohne Prod-Access, neue Codebase ohne DB-Setup):

1. **Code-Grep nach Settern** ist primärer Surrogate:
   ```bash
   grep -rn "mark_<entity>\|set_<col>\|<col>\s*=\s*['\"]" --include="*.py"
   ```
2. **Migration-File** lesen falls vorhanden: oft sind initiale Werte oder CHECK-Constraints dort definiert
3. **Test-Fixtures** in `tests/` zeigen oft die kanonischen Werte (per-Convention `factories/<table>.py`)
4. **Fallback an Caller** (statt zu raten): „Ich brauche `SELECT DISTINCT <col> FROM <table>`-Output bevor ich die WHERE-Klausel finalisieren kann. Kannst du das ausführen oder ist der Output verfügbar?" — explizit als Pflicht-Vorbedingung formulieren, nicht heuristisch raten und hoffen.

→ Diese Option ist legitimer als die Trainingsdaten-Heuristik (`'accept'`/`'accepted'`), weil sie die Unsicherheit explizit ans Caller-Setup zurückspielt statt sie silent in der Query zu vergraben.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS via Subagent-Pair-Dispatch)

- **RED-Subagent** (ohne Skill, Prompt: „Schreibe SQL für 4-Wochen-Accepts auf `v3_signals.user_response`"): schrieb `WHERE user_response = 'accepted'` aus Trainingsdaten-Heuristik. War selbstkritisch in Schritt 3 („Heuristisch geraten, ich habe NICHT geprüft welche distinct-Werte tatsächlich in der Spalte stehen") — erkannte die Lücke aber führte sie nicht aus. Hätte Wolf eine falsche `count=0`-Query geliefert.

- **GREEN-Subagent** (mit Skill, identisches Prompt): Discovery-Query als Schritt 0 vorgeschaltet → `SELECT user_response, COUNT(*) FROM v3_signals GROUP BY user_response`. Erkannte das 27.05.-Beispiel im Skill als 1:1-Match → übernahm `'taken'` als verifizierten Code-Wert. Hat zusätzlich „wenn count=0 nicht naive Schluss" als Anti-Pattern dokumentiert.

- **Refactor angewendet**: Sektion „Discovery-Surrogate ohne Live-DB-Zugriff" hinzugefügt (aus GREEN-Self-Reflection: „Hinweis was zu tun ist wenn Subagent KEINEN Live-DB-Zugriff hat — Skill geht implizit von ausführbarem `psql` aus"). Schließt Caller-Context-Bias für Subagents ohne DB-Tool.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **REST-API-Variant**: Pattern gilt analog für REST-Query-Params mit Enum-typed Filter — separate Sektion „Enum-Discovery für API-Filter (nicht nur SQL)"
2. **GraphQL-Variant**: Schema-Introspection vs Resolver-tatsächliche-Werte — vermutlich gleicher Bug-Klasse, eigene Sektion wert
3. **Cross-Skill-Synergie mit `pre-migration-data-verification`**: bei Migration-Cleanup gilt Discovery PFLICHT auch für die `WHERE` der UPDATE/DELETE-Statements — vielleicht Cross-Reference verstärken

## Querverweise

- Wolf-Maxime „DB-Schema verifizieren vor jeder Query" (CLAUDE.md ult-platform) — Spalten-Verifikation
- Dieses Skill ist die **separate Werte-Verifikation**-Schicht zur Spalten-Verifikation
- `pre-migration-data-verification` (heute promotet) — verwandt: vor Constraint-Add Daten-Verletzungen zählen
- Wolf-Maxime „Gegenthese-Check" (25.05.) — „könnte die 0 falsch sein?" ist Gegenthese die zu Discovery führt

## Real-World-Impact (heute, 27.05.2026)

Forensik-Baseline für Wolf-ultimative-platform Block 2:
- **Initial-Query**: 0 user_accepts in 4 Wochen → Schluss „User-Response-Loop broken"
- **Wolf-Korrektur**: „Doch, Alphabet + Bayer"
- **Werte-Discovery** zeigte: 17 `'taken'`, 0 `'accept'` (Code-Wert ist 'taken')
- **Ergebnis**: Bug war in MEINER Query, nicht im System. Hätte zu falscher Forensik-Schlussfolgerung („User-Response-Pipeline kaputt") geführt — und entsprechend falsche Code-Reparatur-Sessions.

**Zeit-Ersparnis bei korrekter Anwendung**: ~30-60 Min Fehl-Diagnose-Detour vermieden.

## Notes für Skill-Reviewer (nächste Session)

- Falls Skill TDD nicht besteht: möglicherweise nur Wolf-Maxime „DB-Schema vor jeder Query" — eine zusätzliche „Werte vor jeder WHERE"-Klausel reicht.
- Falls TDD stark besteht: könnte projektübergreifend Standard werden (alle SQL-Forensik-Sessions)
- **Variante zu evaluieren**: gilt auch für API-Filter (REST-Query-Params mit Enum)?
