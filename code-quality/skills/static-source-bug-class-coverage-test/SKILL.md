---
name: static-source-bug-class-coverage-test
description: Use when adding regression-test coverage for a Bug-Klasse that manifests as a repeated source-code-pattern across multiple call-sites in the same file (or codebase), NOT a single localized bug. Example today (G3-B1): four `WHERE status<>'open'` aggregations in `status.py` all needed `AND win IS NOT NULL` — Endpoint-Mock-Tests can guard one call-site at a time but force you to mock the entire endpoint plumbing (asyncpg-connect, FastAPI-router, conftest fixtures). Pattern: write a static-source-inspect-test that reads the source file directly via `Path(__file__).resolve().parents[N] / "src/file.py"`, extracts pattern-candidates via regex (e.g. all triple-quoted SQL blocks containing `virtual_trades` AND `sum(CASE WHEN win`), and asserts each candidate contains the fix-marker (`win IS NOT NULL`). Critical: include a Whitelist-Skip for f-String-Templates with externalized variables (`{where_clause}`) that get the fix via their definition-site, not the SQL-block itself — otherwise the test produces False-Positives for already-fixed code. Trigger on phrases like "Bug-Klassen-Coverage-Test schreiben", "alle Aggregationen in File X auf Pattern Y prüfen", "Static-Source-Inspect-Test", "regression guard for the same bug pattern in multiple call-sites", "ich will dass NEUE Aggregationen das gleiche Pattern haben", "warum nicht einfach Endpoint-Mocks für alle 4 Stellen?". Do NOT load for single-call-site Bugs (Endpoint-Mock reicht), for Bug-Klassen die nicht im Source-Pattern erkennbar sind (z.B. Runtime-Logik-Bugs ohne syntaktisches Pattern), oder für Files mit komplexen multi-layer f-String-Verschachtelungen wo False-Positive-Whitelisting unzuverlässig wird (dann Integration-Test gegen Real-DB die saubererere Lösung).
---

# static-source-bug-class-coverage-test

> ✅ **PROMOTED 2026-05-27**: Pattern aus G3-B1 Cockpit-Query-Fix Session. TDD-Pressure-Test bestanden (RED: relativ-Pfad + fragile f-String-Detection; GREEN: `Path(__file__).resolve()` + Triple-Quote-Regex + sauberer Whitelist-Skip). Polish eingebaut: Hinweis zu f-String-concatenated SQL.

## Pattern (Kurzform)

1. **Identifiziere Bug-Klasse als Source-Pattern**: SQL-Block mit X UND ohne Y, async-Funktion ohne Z, etc.
2. **Test lädt File via Read** (`Path(__file__).resolve().parents[N] / "path/to/file.py"`) — KEIN relativer Pfad
3. **Extrahiere Pattern-Kandidaten via Regex** über Triple-Quoted-Strings oder Code-Blocks
4. **Für jeden Kandidaten**: prüfe Fix-Marker-Pattern enthalten
5. **WICHTIG — Whitelist-Skip**: Patterns die via f-String-Substitution den Fix kriegen (`{where_clause}`-Templates) skippen, sonst False-Positives für bereits-gefixten Code
6. **Violations-Liste**: bei Mismatch → assert mit voller Snippet-Liste im AssertionError

> **Limitation**: dieser Test deckt nur triple-quoted SQL-Strings (`"""..."""`) ab. SQL-Strings via f-String-Concatenation (`f"SELECT ... WHERE " + condition`) sind nicht erfasst — bei solchen Patterns ist ein Integration-Test gegen Real-DB die zuverlässigere Lösung.

## Konkretes Beispiel (G3-B1, 27.05.2026)

```python
def test_status_module_no_unfiltered_win_aggregations():
    """Static check: jede sum(CASE WHEN win) Aggregation in status.py
    muss in einem Query-Block sein, dessen WHERE win IS NOT NULL enthält."""
    from pathlib import Path
    import re

    src_path = (
        Path(__file__).resolve().parents[2]
        / "api/routes/dashboard/modules/status.py"
    )
    src = src_path.read_text(encoding="utf-8")

    # Triple-quoted-SQL-Blocks extrahieren
    sql_blocks = re.findall(r'"""(.*?)"""', src, re.DOTALL)

    violations: list[str] = []
    for block in sql_blocks:
        block_lower = block.lower()
        if "virtual_trades" not in block_lower:
            continue
        if not ("sum(case when" in block_lower and "win" in block_lower):
            continue
        # WHITELIST: f-String-Blöcke mit externalisierten where_clause skippen —
        # die werden von den 4 Endpoint-Mock-Tests separat geguarded
        if "{where_clause}" in block:
            continue
        if "win is not null" not in block_lower:
            violations.append(block.strip()[:200])

    assert not violations, (
        "Unfiltered win-Aggregation(s) gefunden in status.py — Bug-Klasse "
        "aus G3-B1 (KW22-Cockpit-Verzerrung) wieder eingeschleust:\n\n"
        + "\n---\n".join(violations)
    )
```

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Naiv alle Pattern-Matches als Violation melden (ohne Whitelist) | False-Positives für Code wo Fix via externalized-Variable kommt → Whitelist-Skip mit klarem Kommentar |
| Pattern-Regex zu greedy (matches mehrere Blocks) | Triple-Quote-Capture mit `DOTALL` + `.*?` non-greedy |
| Test als Endpoint-Integration-Test bauen | 4 Bug-Stellen = 4 Endpoint-Mocks = 4× Setup. Static-Source-Inspect mit 1 Test deckt alle ab |
| File-Path hard-coded oder relativ | `Path(__file__).resolve().parents[N]` — test läuft von beliebigem cwd |
| Violations-Error ohne Snippet-Liste | Test-Failure-Message nutzlos — User weiß nicht WO im File die Violation ist |

## Quick-Reference: wann Static-Source vs Endpoint-Mock vs Integration-Test

| Bug-Klasse | Test-Strategie |
|---|---|
| Source-Pattern in 1 Call-Site | Endpoint-Mock |
| Source-Pattern in N>1 Call-Sites im selben File | **Static-Source-Inspect** (dieses Skill) |
| Source-Pattern über mehrere Files | Static-Source-Inspect über Glob-Pattern |
| Runtime-Logik-Bug ohne syntaktisches Pattern | Real-DB-Integration-Test |
| SQL via f-String-Concatenation (nicht triple-quoted) | Real-DB-Integration-Test |
| Mehr-Layer-f-String-Verschachtelung mit komplexer Substitution | Real-DB-Integration-Test (Whitelist wird unzuverlässig) |

## Real-World-Impact

G3-B1 Cockpit-Query-Fix 27.05.2026: 4 Aggregations-Stellen, 1 Static-Source-Test deckt alle ab plus Regression-Guard für zukünftige Aggregationen. Test fand naiv 4 Bug-Stellen (2 davon False-Positive durch f-String). Verfeinerung auf 2 echte mit Whitelist-Skip war ironisch ein 2-Iteration-Cycle, der Skill macht das in 1.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS)

- **RED-Subagent** (ohne Skill): Wählte ebenfalls Static-Inspection (kein Endpoint-Mock) — überraschend smart. ABER: nutzte relativen Pfad `Path("api/routes/analytics/metrics.py")` (bricht bei anderem cwd), und komplexe heuristische f-String-Variable-Definition-Regex (sucht Var-Definition im ganzen Modul — fragil bei Multi-Modul-Imports). Ehrlichkeits-Vorbehalt selbst benannt.

- **GREEN-Subagent** (mit Skill): `Path(__file__).resolve().parents[2]` korrekt, Triple-Quote-Regex sauber, Whitelist-Skip mit erklärendem Kommentar. Self-Reflection identifizierte Skill-Lücke: f-String-concatenated SQL nicht abgedeckt → Polish-Item eingebaut.

- **Refactor**: kein R1-R3 nötig. Polish-Item (f-String-Concatenation-Limitation-Note) direkt eingebaut.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. Glob-Pattern-Beispiel für "Source-Pattern über mehrere Files" Fall (z.B. `glob("api/**/*.py")` + iterate)
2. `--no-header` / `format-string` Anpassung für Violations-Message wenn Snippet sehr groß
