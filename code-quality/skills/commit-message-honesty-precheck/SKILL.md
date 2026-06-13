---
name: commit-message-honesty-precheck
description: Use before writing or finalizing a git commit message, especially when the subject line uses words like "NO-OP-Fix", "no behavior change", "refactor only", "trivial", "cleanup", "minor", "simple bump", "doc-only" — these phrases are often LIES in disguise that hide real semantic changes. Trigger on phrases like "kleiner Fix", "nur ein Refactor", "NO-OP", "behavior unchanged", "trivial change", "harmless cleanup", "just bumping the default", or before any commit that touches a default value, signature, env-var-fallback, or filter-parameter. Do NOT load for genuinely cosmetic changes (typos, comments-only, whitespace), for first-line spelling, or for non-git contexts (slack messages, jira tickets). Encodes the 2026-06-01 ultimative-platform self-correction: I wrote a commit titled "Z.1-C5 default cap 5→3 (Forensik-belegter NO-OP-Fix)" for a change that blocks 40 trades and shifts WR by +0.43pp — that is NOT a NO-OP. Code-Review-Subagent caught it with Confidence 88 as Important Finding.
---

# commit-message-honesty-precheck

> ✅ **PROMOTED 2026-06-08**: RED-Subagent erkannte "NO-OP" als falsch und schlug bessere Message vor — gute Basis. GREEN-Subagent wendete alle 3 Steps + Smell-Table strukturiert an, quantifizierte den Effekt (40 Trades blockiert, +0.43pp WR), und emittierte "PRECHECK: FEHLGESCHLAGEN — Message ist eine Lüge."

## The pattern

Before finalizing a commit message, especially the subject line:

**Step 1 — List every "no-effect" claim in the message**

Phrases like "NO-OP", "no behavior change", "refactor only", "doc-only", "cosmetic", "trivial", "Default-Anpassung".

**Step 2 — For each claim, compute a behavior-diff proof**

| Smell | Likely lie | What to verify |
|---|---|---|
| "NO-OP" | Change actively blocks/triggers something now | Count rows/trades/calls affected by diff |
| "no behavior change" | Default value or branch condition was touched | grep for old default in tests + production code |
| "refactor only" | Tests were added/removed/renamed | `git show --stat` for new test files |
| "trivial" | Diff touches >1 file or >10 lines | `wc -l` the diff |
| "cosmetic" | Source files (not /docs) were touched | `git diff --stat` by directory |
| "default bump" | A consumer is affected with no opt-in | grep usage of the old default |

**Fallback wenn kein Repo-Zugriff:** Argumentiere aus der Diff-Beschreibung heraus. Zähle Zeilen, identifiziere welcher Code-Pfad vom neuen Default berührt wird, schätze betroffene Aufrufe. "Ich habe keinen git-Zugriff" ist kein Freibrief für die NO-OP-Behauptung.

**Step 3 — Replace lies with measured facts**

Rewrite the subject line to match the actual diff:
- ❌ `"feat(backtest): Z.1-C5 default cap 5→3 (Forensik-belegter NO-OP-Fix)"`
- ✅ `"feat(backtest): Z.1-C5 cap default 5→3 — blockt cc=4/5-Tage (~40 Trades / +0.43pp WR)"`

Korrekte Default-Änderungs-Message (positives Beispiel):
- ❌ `"chore: bump MAX_SIGNALS_PER_DAY 5→3 (harmless default)"`
- ✅ `"fix(z.1): Scoring-Cap 5→3 — empirisch: >3 Signale/Tag binden zu viel Kapital (~40 Trades/Tag betroffen)"`

## The 2026-06-01 trigger case

I had finished a forensic SQL analysis showing Cap=5 as "mathematically NO-OP" (max `confluence_count` in training-VTs = 5, so Cap=5 never fired). Then I changed default to 3 — which blocks cc=4 and cc=5 trades (40 trades, ~7% of Stichprobe, +0.43pp WR shift).

Commit message: **"Forensik-belegter NO-OP-Fix"** — the phrasing was semantically inverse to the actual diff. Reviewer Finding I1 (Confidence 88): "Commit-Message täuscht."

**The trap**: "the old default was a NO-OP" ≠ "this change is a NO-OP". These are logically different claims. When you change a previously-NO-OP default to an active one, the CHANGE is NOT a NO-OP.

## Recovery: when an already-pushed commit has a misleading message

Per Wolf-Maxime "NEW commits rather than amending":
- Do **not** rebase or amend
- **Forward-document** in the next commit's message + daily note
- Example: `"Klarstellung zu 3247e28: ursprüngliche Message 'NO-OP' war irreführend — der Change blockt tatsächlich cc=4/5-Tage"`

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-08 (PASS)

- **RED-Subagent** (ohne Skill): Erkannte "NO-OP" als falsch ("Eine NO-OP-Änderung hat per Definition keinen Effekt"). Schlug bessere Message vor. Fehlte: strukturierte Smell-Table, 3-Step-Flow, Quantifizierung des Effekts (wie viele Trades betroffen?).
- **GREEN-Subagent** (mit Skill): Wendete Smell-Table an ("NO-OP" + "default bump" beide getroffen). Formulierte: "PRECHECK: FEHLGESCHLAGEN — Message ist eine Lüge." Lieferte zwei Varianten der korrekten Message (mit und ohne Quantifizierung). Identifizierte die Kern-Falle: "Intention war NO-OP" ≠ "Diff ist NO-OP".
- **Refactor**: Positives Beispiel für korrekte Default-Änderungs-Message hinzugefügt (fehlte im Original). Fallback-Protokoll für "Precheck ohne Live-Code-Zugriff" ergänzt.

### Cycle-2-Backlog (nicht-blocking)

1. Git hook der commit-message draft scannt und bei Smell-Words warnt (CI-lint-Regel)
2. Multi-Claim-Handling: wenn "NO-OP" UND "minor" kombiniert auftreten — beide prüfen, additive Smells
3. Cross-Repo-Beispiele aus 2+ weiteren Projekten
