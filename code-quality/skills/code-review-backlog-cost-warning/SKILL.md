---
name: code-review-backlog-cost-warning
description: Use when the user/agent is about to push code, merge a feature branch, or claim a body of work as "done" AND no code-review has happened in a while. Specifically trigger when ANY of these hold — (a) >7 days since last `requesting-code-review` invocation on this codebase, (b) >30 atomic commits accumulated since last review, (c) >5000 LoC changed since last review, (d) Pre-Push-Hook code-review-warning has been bypassed ≥2 times in succession (Bypass-Multiplikation), (e) the user types phrases like „wir haben seit Wochen kein Review gemacht", „ich pushe das einfach", „der Hook ist nur warning, ignoriere", „ist doch nur ein kleiner Fix obendrauf". STOP and surface a cost-estimate-warning to the user BEFORE the push — quantify the expected aufzuräumende Backlog-Cost (Wallclock + Token-Budget + Re-Review-Cycles) and offer chunked-parallel-review-dispatch as the alternative. Wolf-Maxime (26.05.2026): „Code-Review muss Standard werden" — encodes the painful proof-by-instance from 10.06.2026 where 4 weeks ohne Review = 5h Wallclock + €50 Token + 21 Commits in 6 Phases + 3 Re-Review-Cycles in ONE Session vs ~10min/Tag bei täglichem Review. Do NOT load for fresh-branches (≤3 commits, ≤500 LoC, ≤2 days), for explicitly-marked WIP-pushes the user asked you to do without review („push einfach, ich review später"), or when running inside a `requesting-code-review`-Session itself (you're already reviewing). Also skip for one-line typo fixes / pure documentation commits. Complements `superpowers:requesting-code-review` (this skill is the warning-before, that skill is the review-during) and `code-review-chunk-dispatch` (this skill recommends it, that skill executes it).
---

# Code-Review-Backlog Cost Warning

> ✅ **PROMOTED 2026-06-10** — TDD Cycle 1 PASS (moderate value-add). RED-Subagent: refusedte den Push korrekt auf Basis der CLAUDE.md-Maxime, aber unstrukturiert und ohne konkrete Cost-Quantifizierung. GREEN-Subagent: lieferte strukturierten Pflicht-Output-Block mit konkreter Cost-Tabelle (45 Commits / 6.200 LoC / 13d → Tabellen-Zeile 4), explizite Option A/B, „Welche Option?"-Stopp gemäß Step 4. Mehrwert: Quantifizierung + Trajektorie-Hinweis (Cycle wiederholt sich gegenüber 10.06. Vormittag). Polish-Items im Cycle-2-Backlog am Ende.

## Overview

Code-Review-Backlogs sind **superlinear teurer** als tägliches Review — nicht linear. Bei 5× so vielen Commits ohne Review ist die Aufräum-Cost nicht 5× sondern 20-50× höher, weil:

- Re-Review-Cycles häufen sich (Fix-1 produziert Fix-2-Bug, Fix-2 produziert Fix-3-Bug)
- Schema-Drifts kumulieren in mehreren Pfaden gleichzeitig
- Pre-Push-Suite-Cycle-Time × #Push-Cycles wird zur dominanten Wallclock-Position
- Wolf muss Domain-Entscheidungen rückwirkend für 4 Wochen Arbeit treffen

**Diese Maxime ist die Cost-Warning-Variante** der Wolf-Maxime „Code-Review muss Standard werden" (26.05.2026). Sie verhindert dass nächstes Mal wieder ein €50-Backlog entsteht weil die Pre-Push-Hook-Warnings „nur eine Warnung" sind.

## When to use

**Trigger-Schwellen (≥1 hinreichend)**:
- ≥7 Tage seit letztem Code-Review auf diesem Repo
- ≥30 atomare Commits seit letztem Review (`git log <last-review-sha>..HEAD --oneline | wc -l`)
- ≥5000 LoC Diff (`git diff <last-review-sha> HEAD --stat | tail -1`)
- ≥2× hintereinander Pre-Push-Code-Review-Hook bypassed (Bypass-Multiplikation)

**Trigger-Phrasen** (User oder du):
- „wir haben seit Wochen kein Review gemacht"
- „pushe das einfach"
- „der Hook ist nur warning, kann ignoriert werden"
- „ist doch nur ein kleiner Fix obendrauf"
- „später machen wir mal ein Aggregate-Review"
- „lass uns erst das Feature fertig machen"

**Hochrisiko-Marker** (zusätzliche Verstärker):
- Mehrere Trading-Pfade / DB-Migrations / ML-Modelle gleichzeitig touched
- Mehrere Wolf-Domain-Entscheidungen sind eingeflossen ohne Test-Belegung
- Pre-Push-Hook ist seit dem letzten Review ≥3× gefeuert (kumuliertes Risiko)

## When NOT to use

- **Fresh-Branch** (≤3 Commits, ≤500 LoC, ≤2 Tage) — Backlog noch nicht aufgebaut
- **Explizit-WIP-Push** vom User („push einfach, ich review später beim Merge")
- **Während eines `requesting-code-review`-Aufrufs** — du reviewst gerade, würdest dich selbst warnen
- **One-Line-Typo-Fixes** / pure Documentation-Commits
- **Hotfix-Druck** (Live-Outage, Trade-Stop) — dann ist „push first, review after" der richtige Reflex, aber **dokumentiere** dass ein Follow-up-Review erforderlich ist

## The 4-Step Warning Flow

### Step 1 — Backlog-Größe messen (nicht schätzen)

```bash
# Wann war der letzte Code-Review-Push?
git log --grep="code-review\|code review\|CR-[A-Z][0-9]" --oneline -5
# Oder: letzter PR-Merge nach Review
git log --first-parent main --oneline -10

# Backlog-Größe ab dem Punkt
LAST=<sha-of-last-reviewed-commit>
git log $LAST..HEAD --oneline | wc -l         # #Commits
git diff $LAST HEAD --shortstat               # LoC + Files
git log $LAST..HEAD --since="7 days ago" --oneline | wc -l  # 7d-Rate
```

Schreibe die 3 Zahlen explizit hin: **Commits / LoC / Tage**.

### Step 2 — Cost-Estimation gegen Schwellen-Tabelle

| Backlog-Größe | Erwartete Aufräum-Cost | Methode |
|---|---|---|
| ≤3 Commits / ≤500 LoC / ≤2 Tage | ~5min, einzelner Subagent | inline review |
| 4-10 Commits / ≤2k LoC / ≤7 Tage | ~15-30min, 1-2 Subagents | `superpowers:requesting-code-review` |
| 11-30 Commits / 2k-5k LoC / ≤14 Tage | ~1-2h, 2-3 chunks | `code-review-chunk-dispatch` (3 Chunks) |
| **>30 Commits / >5k LoC / >14 Tage** | **>3h Wallclock + Re-Review-Cycles + Domain-Entscheidungen** | `code-review-chunk-dispatch` (6+ Chunks parallel) |
| **>70 Commits / >10k LoC / >28 Tage** | **5h+ Wallclock + €50+ Token + 2 Sessions** | **STOPP — Wolf-Warning + Plan-B vorschlagen** |

### Step 3 — User explizit warnen (nicht still arbeiten)

**Pflicht-Output** bevor irgendein Code geschrieben wird:

```
⚠️ Code-Review-Backlog-Warning

Stand: <N> Commits seit <SHA-short> (vor <K> Tagen)
       <M> LoC Diff, <T> Files touched
       Pre-Push-Hook seit <Datum> X× bypassed

Erwartete Aufräum-Cost (siehe `code-review-backlog-cost-warning`):
- Wallclock: ~<Stunden>
- Token-Budget: ~$<Schätzung>
- Re-Review-Cycles wahrscheinlich (Bug-Finding-Rate bei 4 Wochen Backlog: ~3 of 6 Phasen)

Vorschlag:
  Option A — `code-review-chunk-dispatch` (N parallele Subagents, ~1-2h)
  Option B — Continue push + Schmerz später (€50+, 5h+, 2 Sessions)

Wolf-Maxime 26.05.: "Code-Review muss Standard werden"
Wolf-Maxime 10.06.: „...€50 verbrannt..."
```

### Step 4 — Wolf-Entscheidung warten

**Nicht** einfach pushen. **Nicht** einfach Chunk-Review starten. **Wolf wählt** — er hat das Budget-Bewusstsein, du hast nur die Cost-Estimation.

Wenn Wolf Option B wählt: dokumentiere die Wahl in Daily Note („Wolf hat warnung gelesen + bewusst gepusht, Follow-up-Review eingeplant für …").

## Quick Reference

| Frage | Schnell-Check |
|---|---|
| Wann war letzter Review? | `git log --grep="CR-\|code-review" --first-parent -3` |
| Wie viele Commits seitdem? | `git log <sha>..HEAD --oneline \| wc -l` |
| Wie viel Code-Diff? | `git diff <sha> HEAD --shortstat` |
| Wo liegt die nächste Schwelle? | siehe Tabelle Step 2 |
| Welcher Chunk-Skill? | `code-review-chunk-dispatch` (in skills-Liste) |

## Anti-Patterns (was passiert wenn du das ignorierst)

| Anti-Pattern | Erlebter Schaden | Quelle |
|---|---|---|
| „Pre-Push-Hook ist warning, ignoriere" 4×→ 8× bypassed | Backlog wächst von 30 auf 74 Commits silent | 10.06.2026 |
| „Chunks brauchen wir nicht, ein Subagent reicht" | Subagent-Context overflows, Findings unvollständig | 10.06.2026 |
| „Re-Review pro Phase ist Bürokratie" | 3 von 6 Phasen hatten Bugs im ersten Wurf — ohne Re-Review unbemerkt im Live-Code | 10.06.2026 |
| „Tests + Live-Smoke ersetzen Review" | 3 Critical-Bugs waren wochenlang im Live-Trading | 26.05.2026 |
| „Lass uns erst das Feature fertig machen" | Feature wird abgeschlossen, Review niemals nachgeholt | langfristig |

## Cost of Skipping (real)

**Wolf-Quote 10.06.2026 ~14:00**:
> „Die 'Aufräumarbeiten' heute Vormittag haben das komplette Tokenlimit zweier Sessions plus zusätzlich Token für 50€ benötigt. Das kommt davon, wenn man Dinge zu lange liegen lässt."

**Konkret**:
- 74 Commits über 4 Wochen → 5h Wallclock + €50 Token + 21 Reparatur-Commits + 3 Re-Review-Cycles
- 8 Push-Cycles à 9min Pre-Push-Suite = 72min nur für Push-Wallclock
- 5 Critical-Findings + 25 Important-Findings die alle live-bezogen waren
- 6 Implementations-Phasen weil thematisch nicht trennbar nach dem 4-Wochen-Mix

Bei täglichem Review (Wolf-Maxime 26.05.): ~10min × 28 Tage = **4,5h Total** statt 5h-in-einer-Session + €50.

## Red Flags — STOP and warn

- „nur eine kleine Änderung obendrauf"
- „der Hook ist nur warning"
- „das machen wir nächste Woche im Block"
- „ich pushe einfach, später beim Merge gibts Review"
- „4 Wochen ist nicht so lang"

**Alle bedeuten: User-Warning ausgeben, Cost-Estimation zeigen, Chunked-Dispatch als Default-Vorschlag.**

## Cross-References

- **REQUIRED COMPLEMENT**: `superpowers:requesting-code-review` (die Review-Aktion selbst)
- **REQUIRED COMPLEMENT**: `code-review-chunk-dispatch` (für >30-Commit-Backlogs)
- **Wolf-Maxime**: `pre-push-bypass-audit-trail` (für Hook-Bypass-Logging)
- **Quell-Lehre**: `.remember/core-memories.md` § „Code-Review-Backlog wird teurer als tägliches Review"

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-10 (PASS, moderate value-add)

- **RED-Subagent** (ohne Skill, Scenario „45 Commits seit 28.05., 6.200 LoC, User will mit --no-verify pushen"): Hat erstaunlich gut reagiert — refusedte den Push, zog CLAUDE.md-Maxime („Code-Review muss Standard werden") + ähnliche existierende Skills (`code-review-chunk-dispatch`, `pre-push-bypass-audit-trail`) heran. Aber: unstrukturiert, ohne konkrete Cost-Tabelle, ohne quantitative Bug-Cost-Schätzung. Self-Critique listete 6 fehlende Punkte (keine Quantifizierung, keine Audit-Trail-Mechanik, „heute Abend Feature" nicht emotional adressiert, kein Option B, Gegenthese-Check skipped).

- **GREEN-Subagent** (mit Skill): Strukturierter Output mit Schwellen-Tabelle (3 von 4 Schwellen gleichzeitig überschritten), Pflicht-Output-Block 1:1 aus Skill-Template, Cost-Estimation Wallclock+Token+Re-Review-Cycles, explizite Option A (chunk-dispatch jetzt, ~1.5-2h) vs Option B (push + Audit-Trail-Doku + Follow-up-Termin), klarer „Welche Option?"-Stopp gemäß Step 4 — keine vorgreifende Aktion.

- **Vermiedener Anti-Pattern**: GREEN nannte explizit dass ohne Skill „Ok, ich pushe mit --no-verify und du machst Review morgen" → Bypass-Multiplikation Cycle 1 die zur 10.06.-€50-Session geführt hatte.

- **R0** (kein Refactor angewendet): Skill hat alle Kern-Schritte korrekt geliefert. Polish-Items als Cycle-2-Backlog dokumentiert (siehe unten).

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Bypass-Multiplikations-Differenzierung**: 1. Bypass = Warning genug; 2. Bypass = Eskalation. Aktuell liest sich das Skill so als wäre die Multiplikation schon im 1. Bypass-Fall im Gange.
2. **„Feature-Start-Druck"** als explizite When-NOT-Klausel oder eigene Sub-Trigger neben Hotfix-Druck. Aktuell muss man es als Variante von „erst Feature fertig" einordnen — die Subagent hat das gemacht, eine explizite Zeile wäre robuster.
3. **Chunk-Achsen-Mini-Hint** für Step-4-Übergang („typische Chunk-Achsen: thematisch / per-Dir / per-File-Type / per-Domain") — auch wenn der echte Chunk-Skill verlinkt ist, ein Inline-Hint vereinfacht Übergang.
4. **Daily-Note-Template** für Option-B-Doku: aktuell nur „dokumentiere die Wahl", kein konkretes Format. 2-Zeilen-Template würde Audit-Trail standardisieren.
