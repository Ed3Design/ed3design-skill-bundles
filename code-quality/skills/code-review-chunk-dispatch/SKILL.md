---
name: code-review-chunk-dispatch
description: Use when the code-review-backlog is large (>30 commits OR >5,000 LoC changed since last review) AND the caller has Agent/Task-tool dispatch capability (i.e., top-level orchestrator or main Claude session). Trigger on phrases like "code-review-backlog ist groß", "seit Wochen kein Review", "viele Commits ohne Review", "Review von 100+ Commits", "wie reviewe ich diese 200 Commits", "Chunk-Review", "parallel Code-Reviewer Subagents". Do NOT load for single-PR-Review (use superpowers:requesting-code-review direkt), for <30-Commit-Backlog (single subagent reicht), for non-Git-Codebases (chunking-by-SHA-Range setzt git-Workflow voraus), or when running as a subagent yourself without Agent-tool access (the chunk-dispatch pattern is then unexecutable — use risk-based-triage instead, documented in the skill's Fallback section). Complements (sub-of) `superpowers:requesting-code-review` and `superpowers:dispatching-parallel-agents`.
---

# code-review-chunk-dispatch

> ✅ **PROMOTED 2026-05-26**: TDD-Cycle-1 (Caller-Context-Refactor) + TDD-Cycle-2 (Mini-Verify-Fallback-PASS, S3-Pattern-Mode-Value-Prop-CONFIRMED) durch. Auto-Discoverable. Polish-Items aus Mini-Verify-Subagent-Feedback eingebaut: Stichprobe-Definition, Gegenthese-Tiefe-Hierarchie (Critical=Pflicht / Important=Empfohlen / Minor=Optional), tabellarisches Trust-Verdict-Format im Fallback, TDD-Verlauf als Background-Label.

## STOP — Caller-Context-Check (vor allem anderen)

Dieses Skill empfiehlt **Parallel-Dispatch via Sub-Subagents**. Das setzt voraus: **DU (der Caller) hast ein `Agent`/`Task`-Tool**.

**Bevor du irgendwas anderes machst, prüfe**:

| Caller-Check | Aktion |
|---|---|
| Habe ich Zugriff auf das `Agent`-Tool (Top-Level-Orchestrator, Main-Claude-Session)? | ✓ → weiter mit `## Pattern (Kurzform)` und dispatchen |
| Habe ich KEIN `Agent`-Tool (z.B. ich bin selbst ein Subagent)? | → springe zu `## Fallback: Sequential-Triage-Mode` UNTEN. **Versuche nicht das Chunk-Pattern erzwungen-sequenziell anzuwenden.** |

**Anti-Pattern**: Skill blind folgen und sequentiell chunken obwohl du nicht parallel-dispatchen kannst — das ist **schlechter** als natural risk-based-triage. Belegt durch TDD-Test 26.05.2026 (siehe `## TDD-Verlauf` unten): GREEN-Subagent ohne Agent-Tool produzierte SCHLECHTERES Ergebnis (1 statt 4 Critical-Findings, +70% Wallclock) durch erzwungenes Chunking als ein Baseline-Subagent ohne Skill, der natural-risk-based-triage anwendete.

**Rationalisierungs-Falle**:

| Rationalisierung | Realität |
|---|---|
| "Das Skill sagt chunken, also chunke ich sequenziell" | Das Skill setzt PARALLEL-Dispatch voraus. Sequenziell-Chunking liefert die Skill-Promise NICHT, hat aber das Overhead. |
| "Mein Caller hat sicher Agent-Tool, ich bin ja Code-Reviewer" | Prüfe es. Wenn `Agent`-Tool nicht in deinem Tool-Set → du bist ein Subagent. |
| "Ein bisschen Chunking ist besser als gar nichts" | Falsch. Risk-based-Triage ohne artificial-Chunks ist besser dokumentiert (siehe Fallback). |
| "Der Auftraggeber will Chunks sehen" | Der Auftraggeber will gute Bugs. Coverage-Disclosure im Report ist transparenter als chunk-Theater. |

## Pattern (Kurzform)

Wenn der Code-Review-Backlog groß ist (Heuristik: >30 Commits ODER >5,000 LoC ODER >4 Wochen ohne Review):

1. **Scope-Realität messen** — `git log --since`, `git diff --stat`, Commit-Count
2. **Thematische Chunks identifizieren** — ≤15 Commits pro Chunk, ≤6 Chunks total covering High-Stake-Recent-Work, Tail (alt + weniger zeitkritisch) als separater Backlog-Block
3. **Pro Chunk eine BASE_SHA / HEAD_SHA-Range bestimmen** mit `git rev-parse <sha>~1` für inklusive Starts
4. **Parallel-Dispatch** in einem einzigen Message-Block mit mehreren Agent-tool-Invocations (NICHT sequenziell — verschwendet wallclock)
5. **Aggregieren** der Findings nach Critical / Important / Minor + Chunk-Trust-Bewertung (Acceptable / Acceptable-with-fixes / Rollback-suggested)

## Fallback: Sequential-Triage-Mode (wenn du KEIN Agent-Tool hast)

Du bist hier gelandet weil der Caller-Context-Check oben gezeigt hat: du kannst nicht parallel-dispatchen. **NICHT chunken**, sondern risk-based-triage:

1. **Scope messen** wie oben (`git log --since`, `git diff --stat`, Commit-Count) — bleibt nötig für Reporting
2. **Risiko-Domänen identifizieren** statt thematischer Chunks:

| Domäne | Inhalt | Read-Tiefe |
|---|---|---|
| HIGHEST | Money-Path (Trading-Logic, Payments, Auth, Live-Persistierung, Order-Execution) | Volltext-Read aller berührten Files |
| HIGH | Adjacent zur Money-Path (Notifications, Schedulers, Background-Jobs, ML-Inferenz, DB-Migrations) | Volltext-Read der Diff-relevanten Files |
| MEDIUM | Operations / UI / Cockpit | **Stichprobe = mindestens Kern-Methoden (entry points + public API) jedes Diff-relevanten Files lesen, plus gezielte Grep-Pässe für vermutete Anti-Patterns. Files <200 LoC vollständig.** |
| LOW | Tests, Docs, Templates, Legacy-Moves, Config-Reshuffles | Skim via Commit-Messages + `git diff --stat`, nicht line-by-line. Stichprobe nur bei Test-Logik die einen Critical-Fix backstoppt. |

3. **Gezielte Grep-Pässe** für domänen-typische Anti-Patterns (z.B. `_load_*` 2× im selben Statement, `direction.*==.*"LONG"` für Casing-Drift, `cur.execute.*UPDATE.*WHERE` ohne `rowcount`-Check)
4. **Findings nach Severity** wie im Hauptpattern (Critical / Important / Minor)
5. **Gegenthese-Check**: 
   - **Critical → PFLICHT**: kann der Bug eine andere Erklärung haben? Ist die Diagnose belegt mit Code/Schema/Log?
   - **Important → EMPFOHLEN**: bei nicht-offensichtlichen Findings Gegenthese explizit ausschreiben
   - **Minor → OPTIONAL**: nur wenn Reviewer selbst unsicher ist
6. **EXPLICIT-COVERAGE-DISCLOSURE im Report — Pflicht**:
   - Welche Files / Module habe ich VOLLSTÄNDIG gelesen?
   - Welche habe ich STICHPROBE-artig betrachtet?
   - Welche habe ich GAR NICHT gelesen?
   - Damit weiß der Auftraggeber, was die Review NICHT abdeckt → kann gezielt nachfordern.

**Warum kein artificial-Chunking?** Ohne parallelen Dispatch ist Chunking pure-Overhead — es zwingt dich pro Chunk weniger Tiefe zu erlauben, ohne den Throughput-Vorteil zu liefern. Risk-based-Triage skaliert besser auf single-threaded und lieferte im RED-S1-Test mehr Critical-Findings als das erzwungene Sequential-Chunking im GREEN-S1-Test.

**Output-Format für Fallback-Mode** (gleich wie Hauptpattern, plus Coverage-Disclosure + tabellarischer Verdict):
```
## Approach
[Risk-based-Triage, welche Domänen-Tiers wurden wie tief gelesen]

## Coverage-Disclosure
Vollständig gelesen: [Liste der Files]
Stichprobe (Kern-Methoden + Grep): [Liste]
Nicht gelesen: [Liste oder Domain-Beschreibung]

## Findings
### Critical (jedes mit Gegenthese-Check)
### Important (mit Gegenthese-Check bei nicht-offensichtlichen)
### Minor

## Trust-Verdict (tabellarisch, eine Zeile pro Domäne)
| Domäne | Read-Tiefe | Verdict |
|---|---|---|
| HIGHEST | Volltext | Acceptable / Acceptable-with-fixes / Patch-immediately |
| HIGH | Volltext (Diff-relevant) | ... |
| MEDIUM | Stichprobe | ... |
| LOW | Skim | (meist: Acceptable) |

## Empfehlung
SOFORT / IM Backlog / TRIVIAL — was wann?
```

## Konkretes Beispiel (heutige Live-Begegnung)

**Scope-Snapshot**: 246 Commits über 4 Wochen, 287 Files, +44,872 / -1,492 LoC.

**Single-Subagent-Versuch wäre gescheitert**: 44k Zeilen Diff übersteigen Context-Limit. Selbst wenn nicht: Output wäre „Code sieht okay aus, einige TODOs vorhanden" — generisch, kein Befund-Wert.

**Chunk-Aufteilung**:

| Chunk | Range | Commits | Theme | Risk |
|-------|-------|---------|-------|------|
| A | `5e5dd37..9a2cecb` | 4 | Heute Dashboard-Bug+Charts+Race-Fix | mittel |
| B | `1b32427..5e5dd37` | 13 | Gestrige Cockpit Phase B + Phase A Refactor | hoch (Production-deployed) |
| C | `344671a..44c2e09` | 9 | Setup-Detector + ML/Strategic | sehr hoch (Live-Trading) |
| D | `44c2e09..1b32427` | 4 | Telegram-Bot + Dashboard-SSD | hoch |
| E | `<base>..04fb03e` | ~216 | Tail (vor 19.05.) | unbekannt, niedrig (alt) |

→ Chunks A-D = 30 Commits = ~12% des Backlog, aber 100% der High-Stake-Recent-Arbeit. Chunk E als separater Backlog-Item dokumentiert.

**Parallel-Dispatch** in einem Message-Block:
```
<function_calls>
  <Agent description="Review Chunk A" prompt="...">...</Agent>
  <Agent description="Review Chunk B" prompt="...">...</Agent>
  <Agent description="Review Chunk C" prompt="...">...</Agent>
  <Agent description="Review Chunk D" prompt="...">...</Agent>
</function_calls>
```

Wallclock: 10-15 Min für alle 4. Wenn sequenziell: 40-60 Min für die gleiche Output-Qualität.

**Aggregation**:
- 3 Critical (alle in Chunk C — Trading-Logic)
- 11 Important über alle 4 Chunks
- Diverse Minor pro Chunk
- Chunk-Trust-Bewertung: A=Acceptable, B-D=Acceptable-with-fixes, C wegen Critical zusätzlich „patch-immediately"

## Chunk-Strategien (welche Chunks?)

| Strategie | Wann |
|---|---|
| **Thematisch** (Cockpit, ML, Bot) | Wenn Commits klar nach Feature-Themen gruppiert sind |
| **Chronologisch** (pro Woche, pro Sprint) | Wenn keine klaren Themen — fallback |
| **Pfad-basiert** (per Subdir oder Module) | Bei sehr großen Monorepos |
| **Critical-Files-First** (`security/`, `payments/`, Auth) | Bei Stake-Differenzierung |

**Heuristik**: Themen-Cluster sind besser als pure-chronologische Chunks, weil Reviewer-Subagent dann zusammenhängende Logik bewerten kann (z.B. „dieser Refactor + dieser Test + diese Migration") statt verstreute Commits.

## Subagent-Prompt-Template pro Chunk

Jeder Subagent bekommt:
- **Repo-Pfad** (absoluter Pfad, weil Subagent kein conversation-context hat)
- **Chunk-Beschreibung**: was wurde gebaut (1 Absatz)
- **Plan/Requirements-Pointer**: Daily-Note + Spec-Files (Subagent kann die lesen)
- **SHA-Range**: BASE_SHA + HEAD_SHA mit Beispiel-`git diff`-Commandos
- **Review-Checklist** aus `superpowers:requesting-code-review/code-reviewer.md`:
  - Plan-Alignment
  - Code-Quality (separation-of-concerns, error-handling, type-safety, edge-cases)
  - Architecture (security, scalability, integration)
  - Testing (real-behavior vs mocks, edge-cases, integration)
  - Production-Readiness (migrations, backward-compat, docs)
- **Domain-Specific-Linsen** (z.B. „check Display-Name-Maxime", „check numerische Werte-Verifikation")
- **Output-Format**: Strengths + Issues by Severity + Recommendations + Assessment-Verdict

## Aggregation-Pattern

Nach dem Parallel-Dispatch hat man 4 Strukturen. Aggregation:
1. **Critical-Sammel-Liste** über alle Chunks (sortiert nach Risk-Impact)
2. **Important-Sammel-Liste** nach Chunk gruppiert
3. **Minor-Sammel-Liste** kompakt (1-Liner pro Item)
4. **Trust-Tabelle** pro Chunk mit Verdict
5. **Top-Empfehlung**: welche Items SOFORT (Critical), welche IM Backlog (Important), welche TRIVIAL (Minor)

## Anti-Patterns

- ❌ Single-Subagent für 200+ Commits — Output ist generisch
- ❌ Sequenzielle Subagent-Dispatches (40 Min statt 10) — keine Wallclock-Ersparnis
- ❌ Chunks mit überlappenden SHA-Ranges — gleiche Commits werden doppelt reviewed, Findings verdoppelt
- ❌ Tail-Chunk ignorieren ohne Backlog-Eintrag — fällt morgen wieder durchs Raster
- ❌ Findings nicht aggregieren, sondern 4 separate Reports zeigen — User muss selber synthesizen, verliert Übersicht
- ❌ Subagent-Prompts ohne Repo-Pfad (Subagent hat keinen Conversation-Context, weiß nicht wo der Code ist)

## Background: TDD-Verlauf (Bulletproofing-Log)

> Diese Sektion ist Historie + Begründung der Design-Entscheidungen, NICHT Anweisung für den ausführenden Caller. Caller folgt den Sektionen oben (STOP, Pattern, Fallback).

### Cycle 1 — 2026-05-26 (Erkenntnis: Caller-Context-Mismatch)

**RED-S1** (general-purpose-subagent, Repo: ultimative-platform, Range: 04d17098..029c5b7 = 200 Commits / 231 Files / +33,009 LoC, Skill explizit verboten):
- Subagent wählte spontan **risk-based-triage** (Domain-Tiers HIGHEST/HIGH/MEDIUM/LOW)
- Ergebnis: **4 Critical / 9 Important / 6 Minor** mit file:line-Präzision
- Wallclock: 334 s | Tokens: 213k | Tool-Uses: 43
- Inkl. Gegenthese-Check pro Critical, ehrliche Coverage-Disclosure
- Bemerkung am Ende: „Skill existiert laut CLAUDE.md, war mir aber untersagt" → CLAUDE.md-Erwähnung ist confounder, sollte für saubere Tests temporär maskiert werden

**GREEN-S1** (general-purpose-subagent, gleicher Scope, Skill-Direktive: „lade & nutze"):
- Subagent lud das Skill, **konnte aber Parallel-Dispatch NICHT ausführen** (Subagent hat kein Agent-Tool)
- Fallback zu **erzwungenem sequenziellem Chunking** (6 Chunks A-F)
- Ergebnis: **1 Critical (+Re-Verifikation der heutigen Fixes) / 7 Important / 5 Minor**
- Wallclock: 566 s (+70%) | Tokens: 134k (-37%) | Tool-Uses: 54
- Meta-Awareness-Bonus: erkannte „heutige Commits sind selbst Code-Review-Fixes, ich reviewe Re-Reviews"
- **Output objektiv SCHLECHTER als RED** für Bug-Discovery (1 vs 4 Critical) trotz mehr Wallclock

**Skill-Design-Bug entdeckt**: Caller-Context-Mismatch. Skill setzt implizit voraus dass Caller Agent-Tool hat. Bei Subagent-Caller ohne Agent-Tool ist Chunking pure-Overhead und blockiert natural-risk-based-triage.

**Refactor angewendet** (R1+R2+R3, 2026-05-26):
- **R1** (Caller-Context-Guard): neue STOP-Sektion ganz oben, Subagent-Check vor allem anderen
- **R2** (Fallback-Mode): neue Sektion „Sequential-Triage-Mode" mit Risk-based-Triage-Template für Non-Dispatch-Caller
- **R3** (Description-Filter): Description erweitert um „AND caller has Agent/Task-tool" + Do-NOT-load für Subagent-Caller (entfernt zugleich die Description-Trap der Workflow-Summary)

### Cycle 2 — 2026-05-26 (Mini-Verify-Fallback-PASS + S3-Pattern-Mode-Value-Prop-CONFIRMED)

**Mini-Verify-RED** (general-purpose-subagent, 35 Commits, Skill-Direktive „lade & nutze"):
- Subagent las STOP-Sektion ZUERST, erkannte fehlendes Agent-Tool, sprang zu Fallback-Mode (explizit dokumentiert in Skill-Self-Reflection)
- Risk-based-Triage angewendet, **2 Critical (echte Bugs) / 7 Important / 7 Minor** in 380s / 255k Tokens
- Coverage-Disclosure als eigene Sektion, Gegenthese-Check pro Critical
- R1-Guard funktioniert. R2-Fallback-Mode funktioniert. R3-Description filtert korrekt.
- Subagent gab 4 konstruktive Polish-Hinweise zurück (eingebaut: Stichprobe-Definition, Gegenthese-Tiefe-Hierarchie, tabellarischer Trust-Verdict im Fallback, TDD-Verlauf als Background-Label)

**S3-Pattern-Mode-Value-Prop-Test** (top-level-Caller mit Agent-Tool, 80 Commits, 5 parallel dispatched Chunks A-E):
- Wallclock: **488s parallel** vs ~1500s sequenziell-estimated = **3× Speedup**
- Tokens: 581k gesamt (5 Chunks). Pro Finding: **10.4k vs 16k Single-Subagent = 38% Effizienz-Win**
- Findings: **10 Critical / 20 Important / 27 Minor**
  - davon **6 truly-NEW Critical** (4 SOFORT-Items im ultimative-platform: F1-Spec-Drift, UPDATE-after-alerts-append, force_telegram-silent-fail, max_tokens-Truncate-Risk, render_cockpit-not-fail-soft)
  - 4 Critical confirmed-already-fixed via Cross-Chunk-Triangulation (Chunk C + E bestätigen sich gegenseitig)
- Coverage-Tiefe: jeder Chunk las berührte Files VOLLSTÄNDIG (Chunk A: 632 LoC v3_live_monitor.py + 456 LoC tests)
- Trust-Verdicts pro Chunk: A=Acceptable-with-fixes, B=Acceptable-with-fixes, C=Confirmed-fixed-in-follow-ups, D=Acceptable-mit-C1-fix, E=**HIGH-Trust für Critical-Fixes**

**Test-Limitation dokumentiert**: S2 (Grauzone-Threshold-Loophole) + S3-Time-Pressure-Loophole-Test sind mit aktueller Test-Umgebung nicht sauber durchführbar — Subagents haben kein Agent-Tool (Pattern-Mode nicht ausführbar), Top-Level-Caller (Main-Claude) ist im Test-Setup biased durch Skill-Design-Wissen. Pending für zukünftige Tests in „naiven" Sessions ohne Skill-Design-Kontext.

**Status**: PROMOTED. Skill ist auto-discoverable und produktiv einsetzbar.

## Querverweise

- `superpowers:requesting-code-review` — Base-Skill für Single-Review (chunk-dispatch ist sein Multi-Skill-Pendant)
- `superpowers:dispatching-parallel-agents` — Pattern-Base für Parallel-Subagent-Dispatch
- `core-memories.md` „Code-Review muss Standard werden" — Meta-Maxime die regelmäßige Reviews verlangt; chunk-dispatch ist das Heilmittel wenn die Maxime mal eine Weile gerissen ist
- `post-session-skill-review` — was nach erfolgreichem Chunk-Review zu tun ist (Skill-Kandidaten aus Findings extrahieren)

## Real-World-Impact (heute)

Wolf-Pushback 09:30: „komplette Code-Review, seit Wochen nicht gemacht."
- Scope-Messung: 246 Commits / 287 Files / +44k LoC
- Single-Subagent-Versuch wäre fail (Context + Generic-Output)
- Chunk-Strategie: 4 Chunks (A-D) parallel, ~10 Min Wallclock
- Output: 4 detaillierte Reports mit 3 Critical (Trading-Live), 11 Important, diverse Minor
- Folge-Session: 8 von 9 Folge-Tasks abgearbeitet, alle Critical-Bugs eliminiert, alle User-Visible-Bugs gefixt
- **Time-to-Value**: ohne Chunk-Strategie wäre das nicht in einer Session machbar gewesen, Critical-Bugs hätten weiter unter dem Radar gelegen
