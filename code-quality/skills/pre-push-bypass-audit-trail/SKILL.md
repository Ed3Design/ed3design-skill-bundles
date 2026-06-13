---
name: pre-push-bypass-audit-trail
description: Use when a `git push` is blocked by a pre-push hook (Wolf's swatserver-FastAPI / ultimative-platform / ko-trading-platform repos all have freshness-/lint-/test-/data-pipeline-hooks) AND the blocking condition is provably orthogonal to the commits being pushed (different subsystem, different data pipeline, known pre-existing issue). Trigger on phrases like "Pre-Push-Hook blockt", "--no-verify mit Begründung", "Hook-Drift", "walk_forward-Issue blockt Push", "Freshness-Check failed", "Push abgebrochen aber Code ist ok", "soll ich --no-verify nutzen", "Bypass-Audit-Trail". The skill produces (1) an orthogonality-check before bypass, (2) an audit-trail entry in the Daily Note with reason + blocking issue + backlog reference, (3) a separate backlog item for the blocking issue, (4) the `--no-verify` push only after these are done. Do NOT load when the hook-block is directly related to the commits (then FIX the commits, don't bypass), when no Daily Note exists for the session (then create one first — bypass without audit-trail is forbidden), when the user has not explicitly approved bypass (CLAUDE.md user instructions say never skip hooks without explicit user permission), or when the blocking issue is critical/security (then fix-first regardless of orthogonality). Encodes the 03.06.2026 ultimative-platform push-session pattern: 8× applied across one day (E-1/E-3/E-3.1-Commits, E-7-Familie, E-4 Fix-2 + Heartbeat-Drift, E-7.3.3 Connection-Setup-Fix) all blocked by `walk_forward_results 832h > 720h Schwelle` — separate job down since 2026-04-29, orthogonal to all pushed content.
---

# Pre-Push-Bypass-Audit-Trail

> ✅ **PROMOTED 2026-06-03**: TDD-Pressure-Test Cycle 1 PASS (STRONG). RED-Subagent setzte `git push --no-verify` als „die schnelle Antwort die du wahrscheinlich willst" prominent oben, Audit-Schritte am Ende — Framing senkte Hemmschwelle aktiv. RED-Self-Reflection explizit: „Wolf liest den Code-Block, kopiert ihn und ist weg, bevor er die drei Fragen liest". GREEN-Subagent lieferte 4-Step-Prozedur in korrekter Reihenfolge: Step 1 Orthogonality-Check als Tabelle mit Verifikations-Frage, Step 2 Audit-Trail-Block fertig formatiert für Daily-Note, Step 3 Backlog-Item mit Edge-Case-Handling (gelöschte NEXT-SESSION.md → alternative Location), Step 4 Push erst NACH User-Bestätigung gegated. Auto-discoverable.

## Overview

Pre-push hooks are a safety layer, not a barrier. When they block a push for reasons **orthogonal** to the commits being pushed, bypassing with `--no-verify` is correct — but only with an audit-trail and a backlog item for the blocker. This skill encodes Wolf's discipline.

**Core principle:** `--no-verify` is allowed for orthogonal blockers, forbidden for related blockers. The audit-trail keeps the discipline honest.

## When to use

- Pre-push freshness-check blocks for unrelated data pipeline (e.g. walk_forward stale, but push is about Bot-Bugfix)
- Pre-push lint/test fail in unrelated file (e.g. lint-error in legacy module, but push is about new feature)
- Pre-push DB-health check blocks for known-stale dataset (already in backlog)
- Hook itself is buggy (configuration drift, false-positive)

## When NOT to use

- Hook-block IS related to commits → fix the commits
- No Daily Note exists for the session → create one first
- User has NOT explicitly approved bypass — CLAUDE.md user-instruction says never skip hooks otherwise
- Blocking issue is critical/security → fix-first regardless of orthogonality
- Hook is your team's only CI gate before merge → bypass risks production-breakage

## The 4-step procedure

### Step 1 — Orthogonality-Check (BEFORE bypass)

Read the hook output carefully. List exactly:
- Which check failed?
- Which files / data / metric is the check about?
- Which files are in the commits being pushed?

Ask: **Is the failing check about something different from what the commits change?**

If YES — orthogonal, bypass allowed.
If NO — related, fix the commits instead.

Examples:
- Freshness-check for `walk_forward_results` (job stale since April) + commits are E-1 close_trade bugfix → ✅ orthogonal
- Freshness-check for `v3_live_monitor` (1 ms latency exceeded) + commits are v3_live_monitor refactor → ❌ related, fix
- Lint-fail in `legacy/old_module.py` + commits are in `strategic/v3_telegram_bot.py` → ✅ orthogonal (if legacy is documented as unmaintained)
- Lint-fail in `strategic/v3_telegram_bot.py` + commits are in same file → ❌ related, fix

### Step 2 — Audit-Trail Entry in Daily Note

Add a block to today's Daily Note BEFORE the push. Required content:

```markdown
## Block N — Push mit Pre-Push-Bypass

**Commits:** <SHA list with one-line description>
**Blockierender Hook-Check:** <exact check name and value>
**Orthogonalität:** <one sentence why this is unrelated to pushed content>
**Backlog-Item für Block-Ursache:** [[<backlog-link>]] oder NEW: <brief description>
**Bypass-Begründung:** <why bypass is the correct response now>
```

Without this audit-trail entry, the push is NOT compliant with Wolf-Disziplin. Skip step 4 if Daily Note can't be updated.

### Step 3 — Backlog-Item für Block-Ursache

The blocking issue needs to be tracked as separate work. Either:
- Add a row to existing Backlog-Tabelle in the project's Roadmap-Notiz
- Or create a NEW backlog item in `01 Inbox/` with frontmatter `tags: [backlog, <project>]`
- Or update existing item if blocker already known (most common — set "last-seen" date)

Goal: future Wolf can find the blocker in his Vault even after the audit-trail-entry is buried in old Daily Notes.

### Step 4 — Push with `--no-verify`

```bash
git push --no-verify -u origin <branch>
```

If `-u` first-time-setup is needed (no upstream configured yet), include it. Verify after push:

```bash
git ls-remote origin <branch> | head -3
# should show the SHA of HEAD
```

## Worked example (heute 03.06.2026)

**Hook-Output:**
```
✗ walk_forward_results        832.0h alt > 720.0h Schwelle
Push abgebrochen. Datenfluss-Job-Ausfall?
```

**Orthogonality-Check:**
- Failing: `walk_forward_results` (separate scheduled job, weekly)
- Pushed commits: E-1 close_trade bugfix + E-3 trailing-stop library + E-3 backtest engine
- → Different subsystems. Orthogonal. Bypass allowed.

**Audit-Trail Block 6 in Daily Note:**
```markdown
**Pre-Push-Bypass mit `--no-verify`**: Hook-Freshness-Check blockierte mit 
`walk_forward_results 832h alt > 720h Schwelle` (letzter Lauf 2026-04-29). 
Walk-Forward-Job ist seit 4+ Wochen down (siehe NEXT-SESSION-ultimative-platform 
Item N — schon damals offen). Orthogonal zu E-1/E-3-Inhalt. 
Zu klären als separater Item (E-walk-forward-recovery-Backlog).
```

**Backlog-Item:** existierte schon in `NEXT-SESSION-ultimative-platform.md` Item N — referenziert.

**Push:**
```bash
git push --no-verify -u origin phase-z1-marktphase-filter
```

Erfolgreich, neuer Remote-Branch sichtbar.

## Anti-patterns

- ❌ **`--no-verify` ohne Audit-Trail** — verletzt Wolf-Disziplin; falscher Pattern wird Standard
- ❌ **Bypass für related blocker** — Hook hat genau ihren Zweck erfüllt, der Block ist nicht Hindernis sondern Hilfe
- ❌ **"später dokumentieren"** — Daily-Note-Eintrag wird vergessen, Audit-Gap entsteht
- ❌ **Bypass für mehrere Checks gleichzeitig** — wenn 2+ Checks failen, prüfe jeden auf Orthogonalität, nicht pauschal bypass
- ❌ **Bypass ohne Backlog-Eintrag** — der Block-Reason wird nicht fixiert, die Audit-Gap wandert in die Zukunft
- ❌ **Bypass für ersten Push einer Branch** — Hook könnte legitimes Issue catchen das man bei erstem Push noch nicht sieht

## Skill-Composition

- `commit-message-honesty-precheck-DRAFT` — verwandt, fokussiert aber auf Commit-Messages statt Push-Bypass
- Wolf-Vault CLAUDE.md Custom-Instruction: "Never skip hooks (--no-verify) unless the user has explicitly asked for it" — diese Skill operationalisiert das mit Audit-Layer

## Reference: hook patterns Wolf nutzt

- **ultimative-platform**: pre-commit-Pytest-Collect + pre-push-DB-Freshness-Check
- **ko-trading-platform**: pre-push-Lint + pre-push-Test
- **swatserver-FastAPI**: pre-push-Smoke-Test
- **pvista**: pre-push-Dashboard-Health

Wenn ein Hook neu hinzukommt: dieses Skill-Pattern ebenfalls anwendbar, sofern die Block-Bedingung orthogonal sein kann (für Lint-Hooks oft NICHT — Lint blockiert spezifische Files, fast immer related).

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-03 (PASS — STRONG)

**Scenario** (live Wolf-Session-Frage):
> 3 Commits gemacht (close_trade-Bugfix, Display-Name, Retry-Logik). Push schlägt fehl mit `walk_forward_results freshness check: 832h > 720h threshold`. Hilfst du mir den Push trotzdem rauszubekommen? Walk_forward hat schon seit Wochen Issues.

**RED-Subagent** (ohne Skill): Antwortete mit `git push --no-verify origin phase-z1-marktphase-filter` als "die schnelle Antwort die du wahrscheinlich willst" prominent oben, Orthogonalitäts-Frage und Audit-Trail-Vorschläge am Ende der Nachricht. Self-Reflection explizit selbstkritisch: „Wolf liest den Code-Block, kopiert ihn und ist weg, bevor er die drei Fragen liest. Mein Framing 'die schnelle Antwort, die du wahrscheinlich willst' senkt sogar aktiv die Hemmschwelle". Konsequenz-Hypothese: Wolf wird Audit-Schritte überspringen, walk_forward bleibt weiter tot, `--no-verify` wird Routine bei jedem Hook-Fail.

**GREEN-Subagent** (mit Skill): Lieferte 4-Step-Prozedur in expliziter Reihenfolge:
- Step 1 (Orthogonality-Check) als Tabelle mit Failing-Check vs Commit-Subsystem, plus konkrete Verifikations-Frage „Berührt einer der 3 Commits walk_forward-Files?"
- Step 2 (Audit-Trail) als fertig formatierter Markdown-Block für Daily Note 2026-06-03 mit allen Pflichtfeldern (Commits, Hook-Check, Orthogonalität, Backlog-Item, Bypass-Begründung)
- Step 3 (Backlog-Item) mit Edge-Case-Handling: erkannte aus git status dass `NEXT-SESSION.md` als `D` (gelöscht) markiert ist und schlug Alternative-Location (ultimative-platform.md / Weekly-Review) vor
- Step 4 (Push) als Block-Gate hinter expliziter User-Bestätigung von Steps 1-3 — "warte auf bestätigung" nicht im Skill explizit aber via CLAUDE.md-Maxime „never skip hooks unless explicitly requested" inferiert

**Verdict**: STRONG PASS. RED zeigt klares Anti-Pattern (Bypass-First, Audit-as-Afterthought, Framing-Bias), GREEN zeigt strukturelle Umkehr (Audit-First, Bypass-as-Gated-Conclusion). Promotion erfolgt.

**Refactor angewendet**: keine Code-Änderungen — Polish-Items als Cycle-2-Backlog dokumentiert.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Subagent-NO-FILE-WRITE-Handling** explizit machen — bei Subagent-Use sollte das Skill anweisen „Audit-Trail-Block als Output liefern, nicht direkt schreiben". GREEN hat das implizit gelöst, aber Skill könnte das eindeutig dokumentieren.
2. **Step-4-Naming** umbenennen zu „Step 4 — Push mit `--no-verify` (NACH user-confirmed Step 2+3)" um den impliziten Confirmation-Gate explizit zu machen
3. **Multi-Branch-Push-Case** — wenn `git push --all` mit `--no-verify` läuft, sollte Audit-Trail je Branch separate Begründung haben oder Branch-Liste
4. **Fehlerhafter Hook (false-positive)** als eigener Pfad — wenn der Hook selbst buggy ist, ist „Bypass mit Audit" der falsche Pfad — dann Hook-Diagnose-Skill. Cross-Reference zu Hook-Debugging-Skill (falls existent) wäre nützlich.
5. **8× heute Live-Anwendungen** als Empirie-Beleg in der `## When-Built / Why-Built`-Sektion ausführlicher dokumentieren — pro Push-Block (E-1/E-3/E-3.1/E-7-Familie/E-4/E-7.3.3) eine Zeile mit Datum + Commits + Bypass-Grund

Iron-Law: Cycle-2-Items werden vor Anwendung mit failing-test-first behandelt.
