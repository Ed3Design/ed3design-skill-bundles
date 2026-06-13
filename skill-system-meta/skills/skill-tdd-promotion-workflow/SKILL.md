---
name: skill-tdd-promotion-workflow
description: Use when promoting an existing DRAFT/STUB skill (suffix `-DRAFT` or `-STUB` in `name:` field, OR description starts with "STUB —") to GA (auto-discoverable). Different from `superpowers:writing-skills` which covers CREATE-from-scratch — this skill covers the LIFECYCLE-STAGE from "skeleton-exists" to "production-ready". Requires Agent/Task-tool for parallel RED+GREEN-Subagent-Dispatch (Step 3) — if the caller does NOT have Agent-tool (e.g. running as a general-purpose-subagent themselves), STOP and report-up; do NOT silently fall back to name-rename-only. Trigger on phrases like "promote dieses DRAFT-Skill", "TDD für die verbleibenden STUBs", "auto-discoverable machen", "Skill-Promotion-Cycle", "Skill aus -DRAFT entlassen", "TDD-Promotion-Cycle für N Skills". Do NOT load for creating a new skill from scratch (use `superpowers:writing-skills`), for editing GA-skills (just edit), when no DRAFT/STUB-suffix exists (skill is already GA), or when target skill file does not exist (no work to do).
---

# Skill TDD-Promotion-Workflow

> ✅ **PROMOTED 2026-05-27**: Pattern aus Wolf-Cleanup-Day-Session 26.05.2026 (5× erfolgreich angewendet), TDD-Pressure-Test in 27.05.-Promotion-Session bestanden. R1-R3-Refactor angewendet (Pre-Step-0, Caller-Context-STOP-Mode, konkretes Dispatch-Beispiel).

## Lifecycle-Position

`superpowers:writing-skills` deckt **CREATE** ab (RED-GREEN-REFACTOR-Cycle für neue Skills). Dieses Skill deckt **PROMOTE** ab — die andere Lifecycle-Stage:

```
[Idee] → CREATE (writing-skills) → -DRAFT-Suffix → [Skeleton mit TDD-Aufgabe] → PROMOTE (dieses Skill) → GA (auto-discoverable)
```

**PROMOTE-Pflicht**: nicht jeder DRAFT wird zu GA. Manche bleiben deferred (Pattern bewahrt, Trigger nicht aktiv) bis genug Re-Use-Belege da sind.

## Pre-Step-0: Caller-Context + Target-Existence-Check (PFLICHT)

**STOP-Gate vor allem anderen.** Diese beiden Checks scheitern silent und führen zu invaliden Promotions wenn übersprungen.

### Check A — Caller hat Agent/Task-Tool?

```
Hat der aktuelle Caller (= du, der dieses Skill lädt) Agent-Tool im Tool-Inventar?
- TOP-LEVEL Claude Code Session  →  ja  →  weiter
- general-purpose subagent       →  nein →  STOP, siehe „Fallback: No-Agent-Tool-Caller"
- gsd-* spawned agent            →  meist nein →  STOP
```

**Wenn nein → STOP**: Du kannst Step 3 (paralleler RED+GREEN-Dispatch) nicht ausführen. Single-Caller-Simulation ist KEIN Ersatz (du weißt schon was das Skill claimt, RED-Validity verloren). Report-up an den dispatching Caller mit:

> „Cannot execute skill-tdd-promotion-workflow without Agent/Task-tool. Step 3 (parallel RED+GREEN-Subagent-Dispatch) is the validity-load-bearing step and cannot be substituted by single-caller simulation. Promotion-Cycle must be invoked from a top-level Claude Code session that has Agent-tool access."

Siehe „Fallback: No-Agent-Tool-Caller" unten für die einzig legitime Single-Caller-Aktion (Prep-Only-Mode).

### Check B — Target-Skill-Datei existiert?

```bash
test -f ~/.claude/skills/<SKILL-NAME>/SKILL.md && echo "exists" || echo "MISSING"
```

Wenn `MISSING` → STOP und an Caller zurückmelden. Nicht synthetisch eine neue erfinden (das wäre CREATE-Workflow, falsches Skill).

### Check C — Skill ist wirklich DRAFT/STUB?

```bash
head -3 ~/.claude/skills/<SKILL-NAME>/SKILL.md | grep -E "name:.*-DRAFT|name:.*-STUB|description:.*STUB —"
```

Wenn keine Match → Skill ist bereits GA, keine PROMOTE-Arbeit nötig. STOP, ggf. Edit-Mode-Skill verwenden.

## Pattern (10 Steps)

Pro DRAFT/STUB-Skill (nach bestandenem Pre-Step-0):

1. **Skill lesen** (Read-Tool, gesamte Datei) — verstehen was es claimt, welche Trigger-Phrasen, welche Anti-Patterns
2. **RED + GREEN-Scenario designen** — identischer Prompt-Stem, einzige Variable = Skill-Access-Direktive. Scenario muss konkret genug sein dass das Anti-Pattern „natürlich" auftritt (Bait einbauen wenn nötig)
3. **Beide Subagents in EINEM Message-Block parallel dispatchen** — Agent-Tool, `general-purpose`-Subagents (siehe Konkretes Beispiel unten)
4. **Analyse**: gibt RED den natürlichen Anti-Pattern wieder (Failure-Mode), reagiert GREEN compliant? Vergleich entlang der Self-Reflection-Antworten
5. **Refactor wenn nötig** — Caller-Context-Bias-Check ist kritischer Loophole: Subagents haben ggf. weniger Tool-Inventar als Caller, Skill muss das antizipieren
6. **Polish-Items aus Subagent-Self-Reflection** — entweder einbauen oder als Cycle-2-Backlog dokumentieren (siehe Polish-vs-Promote-Decision)
7. **Marker-Strip**: `name:` von `*-DRAFT` / `*-STUB` auf clean umbenennen UND `description:` von STUB-Prefix säubern (BEIDE Felder — Auto-Discovery liest beide; Wolf-Pushback 26.05. Nachtrag 3)
8. **Header-Banner**: ⚠️ DRAFT-STATUS-Block durch ✅ PROMOTED-Banner mit Test-Datum + Verdict ersetzen
9. **TDD-Verlauf-Sektion** als Background appendieren (Cycle 1 Erkenntnisse + Cycle-2-Backlog)
10. **Commit** als atomic `feat: promote <skill-name> ...` mit Test-Verdict

## Konkretes Dispatch-Beispiel (Step 3)

So sieht ein RED+GREEN-Dispatch-Pair in einem Message-Block aus (gekürzt):

```python
# RED-Subagent (ohne Skill)
Agent(
    subagent_type="general-purpose",
    description="RED-X <skill-shortname>",
    prompt="""
Du bist Teil eines TDD-Pressure-Tests. Du bist die RED-Baseline (ohne Skill).

**CONSTRAINT**: Du darfst KEINEN Skill mit dem Namen `<skill-name>` laden.

**Scenario**: <konkrete Aufgabe mit eingebautem natural-Anti-Pattern-Bait>

**Honesty-Direktive**: Sei ehrlich wie du vorgehst. Wenn du heuristisch antwortest, sag das.

**⚠️ NO-FILE-WRITE**: Schreibe KEINE Dateien auf Disk. Alle Code-Beispiele als Markdown-Code-Blocks in deiner Antwort — NICHT als Dateien im Working Directory. Der CWD kann ein Obsidian-Vault oder ein Produktions-Repo sein — Dateien dort erzeugen Ghost-Nodes oder Datenmüll.

Report-Format: <Aufgabe-spezifisch>
"""
)

# GREEN-Subagent (mit Skill) — IM SELBEN Message-Block parallel dispatched
Agent(
    subagent_type="general-purpose",
    description="GREEN-X <skill-shortname>",
    prompt="""
Du bist GREEN-Subagent (mit Skill).

**SKILL-DIREKTIVE**: Lies ZUERST via Read-Tool die Datei `/Users/<user>/.claude/skills/<skill-name>/SKILL.md` (NICHT via Skill-Tool, da DRAFT-Status auto-discovery blockiert). Folge dann seinen Anweisungen.

**Scenario**: <identisch zu RED>

**⚠️ NO-FILE-WRITE**: Schreibe KEINE Dateien auf Disk. Alle Code-Beispiele als Markdown-Code-Blocks in deiner Antwort — NICHT als Dateien im Working Directory. Der CWD kann ein Obsidian-Vault oder ein Produktions-Repo sein — Dateien dort erzeugen Ghost-Nodes oder Datenmüll.

Am Ende, Sektion `## Skill-Self-Reflection`:
1. Welche Sektion des Skills hast du zuerst gelesen?
2. Hattest du Zugriff auf die Tools die das Skill voraussetzt? (Caller-Context-Check)
3. Welche der Pattern-Schritte hast du umgesetzt? Welche übersprungen + warum?
4. Welche „natürliche falsche Empfehlung" hat das Skill dich vermeiden lassen?
5. Was war hilfreich / unklar / fehlend?
"""
)
```

**Wichtig für Step 3**:
- Beide Calls in EINEM Message-Block (parallel-Dispatch, nicht sequenziell)
- `description`-Feld kurz halten, prefix mit `RED-` / `GREEN-`
- Skill-Pfad immer via Read-Tool angeben (DRAFT-Status blockiert Skill-Tool-Auto-Discovery)
- Bei N Skills: 2N Agent-Calls in einem Block (z.B. 8 Skills = 16 Calls)

## Caller-Context-Bias-Check (CRITICAL Loophole)

Subagents (general-purpose) haben **kein Agent/Task-Tool**. Wenn das zu promotende Skill `superpowers:dispatching-parallel-agents` oder ähnliches als Kern-Mechanik voraussetzt, wird der GREEN-Subagent das Pattern nicht ausführen können → GREEN-Test scheitert silent ODER produziert sequentiellen Fallback der schlechter als Baseline ist.

**Pflicht-Check vor RED+GREEN-Dispatch des zu testenden Skills**:
- Welche Tools setzt das Test-Skill voraus? (Bash? SSH? Agent? MCP?)
- Hat ein general-purpose-Subagent diese Tools?
- Wenn nein: das Test-Skill muss eine STOP-Sektion + Fallback-Mode haben (siehe `code-review-chunk-dispatch` als Vorbild; siehe DIESES Skill für Self-Reference)

**Beispiel** (chunk-dispatch, 26.05.2026): GREEN-Subagent erreichte sequenziell-erzwungenes Chunking statt Parallel-Dispatch → schlechter als RED-Baseline (1 Critical vs 4). R1+R2+R3-Refactor mit Caller-Context-Guard + Fallback-Mode + Description-Filter nötig vor Promotion.

**Beispiel** (skill-tdd-promotion-workflow selbst, 27.05.2026): GREEN-Subagent erkannte „kein Agent-Tool, STOP" — das Skill hatte aber selbst keinen STOP-Mode dokumentiert. Iron-Recursion gefunden, Refactor (dieser Block + Pre-Step-0) angewendet.

## Fallback: No-Agent-Tool-Caller (Prep-Only-Mode)

Wenn Pre-Step-0 Check A scheitert (Subagent-Caller ohne Agent-Tool), gibt es genau EINE legitime Aktion:

### Prep-Only-Mode

1. **Lese das Target-Skill** (Read-Tool)
2. **Schreibe ein PROMOTION-PLAN.md** neben das Target-Skill mit:
   - RED-Subagent-Prompt-Vorschlag (komplett, copy-paste-ready)
   - GREEN-Subagent-Prompt-Vorschlag (komplett, copy-paste-ready)
   - Erwarteter RED-Anti-Pattern (Hypothese)
   - Erwarteter GREEN-Compliance-Check
   - Caller-Context-Bias-Risiko für das Target-Skill
3. **Report-up**: „Prep done, file: PROMOTION-PLAN.md. Top-level-caller mit Agent-Tool muss Dispatch ausführen."

### Was Prep-Only-Mode NICHT macht

❌ Single-Caller-RED+GREEN-Simulation (Validity verloren — du weißt schon was das Skill claimt)
❌ Nur name-Rename (Iron-Law-Anti-Pattern: PROMOTE ohne RED-Test)
❌ Heuristisches „sieht gut aus, ich promote"
❌ Header-Banner / Description-Strip vor erfolgtem TDD

## Polish-vs-Promote-Decision

Subagent-Self-Reflection (siehe `subagent-self-reflection-prompt-pattern`-Skill) liefert oft 3-5 Polish-Items pro Skill. Entscheidung pro Item:

| Item-Typ | Action |
|---|---|
| Sub-Skill-essential (z.B. unklarer Trigger, fehlender STOP-Mode) | jetzt einbauen vor PROMOTE |
| Edge-Case-Doku (z.B. „was wenn X NULL ist") | jetzt einbauen wenn ≤5min |
| Pattern-Erweiterung („wäre noch nützlich für Y") | Cycle-2-Backlog in TDD-Verlauf, nicht-blocking |
| Tool-Wrapper-Refactor (groß) | separate Session |

Iron-Law: jeder Polish-Edit nach PROMOTE braucht eigenen failing-test-first. Vor PROMOTE können Polish-Items als Teil des Promotion-Refactors mit-eingebaut werden.

## TDD-Verlauf-Sektion-Convention

Jedes promotete Skill bekommt am Ende eine `## Background: TDD-Verlauf (Bulletproofing-Log)` Sektion mit:

```markdown
### Cycle 1 — YYYY-MM-DD (PASS/FAIL)

- **RED-Subagent** (ohne Skill, Prompt: ...): Verhalten beschrieben verbatim
- **GREEN-Subagent** (mit Skill, gleicher Prompt): Verhalten beschrieben verbatim
- **Refactor angewendet**: R1/R2/... was geändert wurde + warum

### Cycle-2-Backlog (Polish, nicht-blocking)

1. [Polish-Item 1]
2. [Polish-Item 2]
...
```

Diese Sektion ist Background für ausführende Caller, nicht Anweisung. Macht aber Skill-Reife sichtbar für künftige Reviewer.

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Skill ohne RED-Test promoten weil „sieht intuitiv okay aus" | RED-Test ist Pflicht — zeigt natürliches Anti-Pattern, validiert Skill-Wert |
| Pre-Step-0 skippen weil „der Skill existiert sicher" | Existence-Check ist 1s, falsch-Annahme kostet 30min |
| RED und GREEN sequenziell statt parallel dispatchen | Parallel im selben Message-Block, einziges Variable = Skill-Access |
| Caller-Context-Bias-Check skippen weil „der Subagent macht das schon" | Subagents haben oft anderes Tool-Inventar — Skill muss Fallback-Mode haben |
| Single-Caller-Simulation als Ersatz für RED+GREEN-Subagent-Dispatch | Validity verloren (Caller kennt schon Skill-Claim) — Prep-Only-Mode statt |
| Nur `name`-Feld strippen, `description`-STUB-Prefix vergessen | Auto-Discovery liest BEIDE Felder (Wolf-Pushback 26.05. Nachtrag 3) |
| Alle Polish-Items vor PROMOTE einbauen wollen | Iron-Law: jeder Polish nach PROMOTE braucht failing-test. Cycle-2-Backlog für non-blocking ist legitim. |
| PROMOTE ohne TDD-Verlauf-Sektion | Spätere Reviewer wissen nicht ob Skill bulletproof ist oder noch DRAFT-Quality |
| **NO-FILE-WRITE-Constraint in Subagent-Prompts vergessen** | Subagents erben den Session-CWD (z.B. Obsidian-Vault oder Production-Repo). Ohne explizites Verbot schreiben sie RED/GREEN-Simulation-Outputs als Dateien dorthin → Ghost-Nodes im Graph / Datenmüll. Korrekt: `⚠️ NO-FILE-WRITE` in JEDEN Subagent-Prompt. Encodes: 27.05.2026, 19 Simulationsartefakte im Vault erzeugt + nachträglich gelöscht. |

## Querverweise

- `superpowers:writing-skills` — CREATE-Stage (vor diesem Skill)
- `subagent-self-reflection-prompt-pattern` — Polish-Item-Quelle pro Subagent-Dispatch
- `superpowers:dispatching-parallel-agents` — Mechanik für Step 3
- `superpowers:test-driven-development` — Iron-Law-Basis
- `code-review-chunk-dispatch` — bestes Beispiel für Caller-Context-Bias-Refactor (Vorbild)

## Real-World-Impact

**Wolf-Cleanup-Day 26.05.2026**: 5 Skills promoted in einer Session via diesen Workflow:
- chunk-dispatch (Cycle-1-Refactor + Cycle-2-Value-Prop)
- asyncpg-decimal-test-shape (trivial-PASS)
- cross-repo-stack-cockpit-pattern (moderate value-add, baseline gut)
- htmx-outerhtml-load-loop (RED reproduzierte exact-Anti-Pattern)
- macos-launchagent-fda-pattern (RED fiel auf Lesson-1-Trap)

**Wolf-Promotion-Day 27.05.2026**: 8 Skills promoted via diesen Workflow (inkl. dieser Self-Application):
- external-advisor-output-plausibility-audit
- legal-paragraph-recommendation-checklist
- pre-migration-data-verification
- pytest-venv-first-triage
- roadmap-phase-execution-verify-first
- skill-tdd-promotion-workflow (DIESER — ironic-recursion: self-applied)
- subagent-self-reflection-prompt-pattern
- vault-decision-cross-file-sync

Token-Cost: ~0.5M pro 5 Skills (8-16 parallele Subagents = 1 großer Dispatch). Wäre ohne Workflow: re-discovery jedes Promotion-Cycles, Caller-Context-Bias-Bug hätte beim ersten Skill nicht entdeckt → restliche wären verbockt promoted worden.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS via Self-Application)

- **RED-Subagent**: Mechanischer Rename-only-Approach (1. Skill lesen, 2. name-Feld DRAFT-Suffix strippen, 3. description STUB-Prefix raus, 4. Header-Banner löschen, 5. TDD-Aufgabe-Sektion löschen, 6. Commit). Eigene Selbstkritik am Ende listete 7 Lücken auf (keine TDD-Verifikation, keine Cross-Skill-Konsistenzprüfung, keine TDD-Aufgaben-Abarbeitung-Check, kein Rollback-Pfad, keine Wolf-Rückfrage, kein Pfad-Schema-Check) — RED erkannte die Lücken, hätte sie aber nicht angewendet ohne Skill.

- **GREEN-Subagent**: Erkannte beim Pre-Step Caller-Context-Bias EXPLIZIT — „Ich als general-purpose-Subagent habe KEIN Agent/Task-Tool, Step 3 (paralleler Subagent-Dispatch) ist physisch nicht ausführbar." Stoppte korrekt statt zu fingieren. Identifizierte zusätzlich: (a) Pre-Step-0 (Existence-Check) fehlt im Skill, (b) Single-Caller-Fallback-Mode predigt das Skill für andere aber lebt es selbst nicht (predigt es im Caller-Context-Bias-Check-Block, hat aber selbst keinen Block dafür), (c) Step-3-Dispatch-Mechanik fehlt konkretes Beispiel.

- **Refactor angewendet (R1+R2+R3)**:
  - **R1** (Pre-Step-0): Caller-Context-Check + Target-Existence-Check + DRAFT-Status-Check als STOP-Gate vor Pattern hinzugefügt
  - **R2** (Fallback-Mode): „No-Agent-Tool-Caller → Prep-Only-Mode" Sektion mit klarer Anti-Liste (was Prep-Only NICHT macht)
  - **R3** (Konkretes Dispatch-Beispiel): Python-Pseudocode-Block mit RED+GREEN-Agent-Call-Paar als Step-3-Konkretisierung
  - Bonus: Anti-Patterns-Tabelle um Pre-Step-0-skip + Single-Caller-Sim erweitert

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Beispiel-Output-Galerie**: konkrete RED+GREEN-Output-Auszüge pro Skill-Typ (trivial-PASS / moderate / refactor-needed) zur Kalibrierung was als „strong RED-Anti-Pattern" zählt
2. **Token-Cost-Heuristik**: bei N Skills, geschätzt 2N×~50k = N×100k Tokens; bei N>8 ggf. Welle-A/B-Split
3. **Test-Skill-Tool-Inventory-Tabelle**: häufige Tool-Sets (general-purpose / gsd-* / specialist) mit „kann Skill X testen ja/nein"-Hint
4. **`/gsd-promote-skill <name>`-Orchestrator-Command**: wenn dieser Workflow >10× pro Quartal läuft, lohnt eigener Slash-Command
5. **Cross-Skill-Konsistenz-Check** (aus RED-Selbstkritik): vor PROMOTE prüfen ob Trigger-Phrasen mit anderen GA-Skills kollidieren — `grep -l "<trigger-phrase>" ~/.claude/skills/*/SKILL.md`
6. **Step 7b — Promotion-Checklist-Sektion entfernen** (aus 12.06.2026-Anwendung): viele DRAFT-Skills haben „## Promotion-Checklist (TDD später)"-Sektion. Bei Promote als Step 7b nach name-Strip entfernen, sonst dangling-Sektion in promotierter Datei. Pattern: `grep -A 10 "## Promotion-Checklist"` + Edit zum Löschen.
7. **Empirik-Update 12.06.2026** (8 Skills in einem 16-Agent-Block): ~430k Tokens total für 8-Skill-Promotion-Cycle. Bestätigt N×100k-Heuristik (Item 2). Skill-Catalog-Wachstum: +8 GA-Skills in einer Session ohne Cycle-2-Refactor-Bedarf — höchster Durchsatz bisher. Cycle-2-Polish-Items pro Skill durchschnittlich 3-5, alle aus GREEN-Subagent-Self-Reflection direkt verwertbar. 16-Agent-Block ROI ~50% Saving vs sequentiell — gleicher Faktor wie 11.06. Spätabend 8-Agent-Block für 4 Skills.
