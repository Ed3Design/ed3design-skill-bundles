---
name: pytest-venv-first-triage
description: Use when pytest shows multiple failures or errors (especially ModuleNotFoundError clusters) and you're about to dig into individual test fixes. ALWAYS check the Python-environment FIRST — `which python3` vs `venv/bin/python3` — before debugging individual tests. System-Python frequently lacks project-deps (cachetools, asyncpg, etc.) while project venv has them. Trigger on phrases like "pytest zeigt viele failures", "test errors after pull", "these tests were green yesterday", "ModuleNotFoundError multiple files", "pre-existing failures", "tests broken without code change", "ImportError test sweep". Do NOT load for single-test-fail debugging (use systematic-debugging directly), for Python projects without venv (no env-mismatch possible), or for failures with clear test-logic-bugs (e.g. assertion errors with concrete values).
---

# pytest venv-first Triage

> ✅ **PROMOTED 2026-05-27**: TDD-Pressure-Test bestanden mit interessanter Variabilität. RED-Subagent erkannte selbst das env-Mismatch-Pattern (smart-RED) und empfahl env-Check vor code-debug — aber mit längerer Begründungs-Tour. GREEN-Subagent lieferte identische Diagnose in <60s via Quick-Check-Procedure-Block + Pattern-Match-Confidence aus Skill-Daten. Skill ist als Tempo-Booster + Insurance-gegen-weniger-smarte-Subagents wertvoll. Cycle-2-Backlog: direnv/pyenv/poetry/uv-Erwähnung, pre-commit-Hook-Hinweis, Makefile-`make test`-Pattern.

## Pattern (Kurzform)

**Vor jedem pytest-Failure-Debug-Dive**: prüfe ob du das richtige Python-Environment nutzt.

```bash
# 1. Welche python3 verweist auf welches Environment?
which python3
python3 -c "import sys; print(sys.prefix)"

# 2. Gibt es einen Projekt-venv?
ls -d venv 2>/dev/null && ls venv/bin/python*

# 3. Wenn ja: re-run mit venv-python
venv/bin/python3 -m pytest <gleiche args> -q
```

Wenn (3) drastisch andere Failure-Counts liefert → 90% der „pre-existing failures" waren Environment-Mismatch, nicht Code-Bug.

## Symptome (woran erkennt man dass es venv ist)

- **ModuleNotFoundError-Cluster** in einem Sub-Verzeichnis (z.B. alle Tests in `tests/test_dashboard/` failed → vermutlich import-error in einer geteilten Datei dieses Subdir)
- **„Diese Tests waren doch grün"** — nichts am Code wurde geändert, aber pytest zeigt 30+ Failures
- **`sys.prefix` zeigt `/Library/Frameworks/Python.framework/...`** statt `/path/to/project/venv`
- **`which python3`** zeigt `/usr/local/bin/python3` oder `/usr/bin/python3` statt `venv/bin/python3`
- pre-commit-Hook lief erfolgreich aber lokaler full-suite-Run failed (Hook nutzt vielleicht system-python, lokal sollte venv sein)

## Konkretes Heutiges Beispiel (26.05.2026)

Wolf full-suite-Run: 1894 passed, **15 failed, 32 errors**. Triage-Verdacht: pre-existing failures. Detailed look auf erste Error:

```
ERROR tests/test_dashboard/test_cockpit_page.py::test_status_page_returns_200
    from cachetools import TTLCache
E   ModuleNotFoundError: No module named 'cachetools'
```

Check:
```bash
$ grep -i cachetools requirements.txt
cachetools>=5.3  # in requirements ✓

$ which python3
/usr/local/bin/python3                              # ← system-python

$ python3 -c "import sys; print(sys.prefix)"
/Library/Frameworks/Python.framework/Versions/3.14  # ← Apple Python.framework

$ ls venv/bin/python*
venv/bin/python3                                    # ← venv existiert

$ venv/bin/python3 -c "import cachetools; print(cachetools.__version__)"
cachetools OK: 7.1.1                                # ← venv hat es
```

Re-Run mit venv-python: **1946 passed, 1 failed** (echter Test-Bug, schnell gefixt). 47 von 48 Failures waren env-Mismatch.

## Diagnose-Tabelle

| Symptom | Ursache | Action |
|---|---|---|
| `which python3` = system-pfad + venv-Dir existiert | venv nicht aktiviert | `venv/bin/python3 -m pytest ...` oder `source venv/bin/activate` |
| ModuleNotFoundError für Module aus requirements.txt | venv installed alle deps, system-python nicht | venv nutzen |
| pre-commit OK, lokal failed | Hook + lokal nutzen verschiedene Pythons | beide auf venv normalisieren |
| CI grün, lokal failed | CI nutzt requirements-installed Container, lokal system-python | venv nutzen |
| Failures in einem Subdir-Cluster | gemeinsamer Import in Subdir crasht alle Tests | nach env-Check Code-Diff prüfen |
| Failures verteilt + ohne Module-Pattern | echter Code-Bug | normaler Debug-Workflow |

## When NOT to use (echter Code-Bug-Indikatoren)

- Failures sind verteilt über viele Subdirs OHNE gemeinsames Import-Module
- AssertionError mit konkreten erwarteten-vs-tatsächlichen Werten
- Failure-Count ändert sich nicht zwischen system-python und venv-python
- Failures begannen erst nach einem konkreten Commit-Sweep (file-path-diff dann hilfreich)

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Sofort in test-by-test Debug einsteigen weil „32 Failures sind echt" | ERST env-Check (30 Sekunden), DANN Debug |
| `pip install <missing-module>` ins system-python statt venv-Switch | Im venv landest du in requirements.txt-Konsistenz; system-pip-install kollidiert mit Brew/Apple-Python-Updates |
| Annehmen pre-commit-Hook nutze venv (tut er evtl. nicht) | Pre-commit-Config explizit checken: `cat .pre-commit-config.yaml \| grep python` |
| Failures als „pre-existing acceptable" markieren ohne env-Check | Du bist evtl. die einzige Person die die Tests jemals fährt — niemand sah die Failures vorher |
| 30+ Minuten in Code-Diff-Triage verbringen ohne env-Check | Env-Check ist 30s, file-path-diff kann immer noch nach env-Check folgen |

## Quick-Check-Procedure (60 Sekunden)

```bash
# Diagnose-Block — copy-paste-fähig
echo "=== Active Python ==="; which python3
echo "=== sys.prefix ==="; python3 -c "import sys; print(sys.prefix)"
echo "=== venv exists? ==="; ls -d venv 2>/dev/null && echo "YES" || echo "NO"
[ -x venv/bin/python3 ] && echo "=== venv python ==="; venv/bin/python3 -c "import sys; print(sys.prefix)"
echo "=== requirements check ==="
[ -f requirements.txt ] && head -10 requirements.txt

# Falls system-python aktiv + venv existiert → re-run:
venv/bin/python3 -m pytest <vorherige args> -q 2>&1 | tail -5
```

## TDD-Aufgabe für nächste Skill-Building-Session

1. **RED**: Subagent ohne Skill bekommt pytest-Output mit 32 ModuleNotFoundError-Errors. Beobachten: dive er direkt in code-debug oder fragt erst env? Wahrscheinlich: code-debug.
2. **GREEN**: Mit Skill: gleiche Task. Sollte ERST env-Check + Quick-Check-Procedure laufen lassen.
3. **REFACTOR**: Loophole „Aber die requirements.txt enthält cachetools, also ist pytest grün ja sicher in venv" → Skill muss explizit machen dass requirements ≠ activated venv.
4. **Trigger-Phrasen**: „pytest viele failures", „tests broken without code change", „ModuleNotFoundError multiple" → wird Skill auto-getriggert?

## Querverweise

- `superpowers:systematic-debugging` — Übergeordnetes Debug-Framework, dieses Skill ist Spezialfall „first check env"
- `swatserver-fastapi-iteration` — Repo-spezifische Python-Setup-Conventions

## Real-World-Impact (Wolf-Cleanup-Day 26.05.2026)

Initial-Run mit system-python:
- 1894 passed, 15 failed, 32 errors (47 vermeintliche pre-existing-failures)
- Triage-Verdacht: in Code-Debug einsteigen würde ~1-2h kosten

Mit venv-python re-run:
- 1946 passed, 1 failed (echter Bug, 5min Fix)
- Real-Saving: ~30-60 Min vermieden, plus Vertrauen gewonnen dass tatsächlich nichts substantielles broken war

Wäre dieses Skill verfügbar gewesen: 60s env-check sofort, 5min real-bug-fix, fertig.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS — mit Variabilitäts-Note)

- **RED-Subagent** (ohne Skill, 47-Failures-Diagnose-Task): Bemerkenswert smart — erkannte selbst dass `requirements.txt` enthält cachetools aber Import scheitert → env-Mismatch-Hypothese. Schlug env-Check vor code-debug vor. Gegenthese-Check explizit gemacht („könnten die 15 Failures echte Code-Bugs sein? — weiß ich noch nicht, erst Env fixen"). Sehr nahe am GREEN-Verhalten.
- **GREEN-Subagent** (mit Skill, gleicher Prompt): Identische Diagnose-Logik, aber strukturierter (Quick-Check-Procedure-Block aus Skill 1:1 übernommen) + höhere Confidence durch Pattern-Match mit dokumentiertem 26.05.-Realfall (gleiche Pfade, gleicher Modul, gleicher Cluster). Verifikations-Schritte präziser.
- **Verdict**: GREEN nicht überlegen über *diesen* RED — aber RED-Subagent-Variabilität ist real (manche Subagents würden direkt in code-debug springen). Skill bleibt wertvoll als Tempo-Booster + Insurance.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **direnv / pyenv / poetry / uv** als alternative venv-Indirektionen erwähnen (`which python3` kann irreführen)
2. **pre-commit-Hook-Konsistenz-Tipp**: nach venv-Switch sollte `pre-commit run --all-files` denselben Output liefern
3. **Defensive Maßnahmen nach Fix**: `.envrc`-Snippet oder `Makefile`-Target `make test` zur dauerhaften Vermeidung
4. **Fallback ohne venv-Dir** (Test-Scenario heute): „falls kein venv: erst `python3 -m venv venv && pip install -r requirements.txt` bevor du den Re-Run versuchst" als robusterer Branch
