---
name: subagent-self-reflection-prompt-pattern
description: Use when dispatching a subagent to test a skill, evaluate a tool, or perform any non-trivial task where YOU (the caller) want meta-feedback about the experience — what worked, what was unclear, what was missing. Include a mandatory "## Skill-Self-Reflection" section in the prompt asking 3-4 introspective questions. Without this, you only get task-output, not improvement-signal. Trigger on phrases like "Subagent für skill-test dispatchen", "Skill TDD pressure-test", "evaluate this tool via subagent", "subagent meta-feedback", "wie nütze ich subagents für skill-verbesserung". Do NOT load for production-task-dispatch (only output matters, not reflection), for performance-critical dispatches (reflection adds tokens), or when caller already has strong skill-content-hypothesis to test against (then use direct A/B comparison instead).
---

# Subagent Self-Reflection Prompt Pattern

> ✅ **PROMOTED 2026-05-27**: TDD-Pressure-Test bestanden. RED-Subagent schrieb Standard-Task-Prompt MIT Trap aber OHNE Self-Reflection-Sektion (exakt das natürliche Anti-Pattern). GREEN-Subagent verwendete GREEN-Variante-Template aus dem Skill, baute 5 strukturierte Fragen am Ende ein (nicht am Anfang!), adaptierte F3 an Single-Pattern-Skill-Charakteristik. Cycle-2-Backlog: „Wie viel vom Test-Ziel im Prompt verraten"-Heuristik-Tabelle, Fragen-Adaption-Hinweis für Multi-Mode-Skills.

## Core Pattern

Wenn du einen Subagent dispatchst um ein **Skill zu testen** oder ein **Tool zu evaluieren**, append eine `## Skill-Self-Reflection`-Sektion zum Prompt mit 3-4 introspektiven Fragen.

**Ohne diese Sektion**: Du bekommst nur den Task-Output. Du weißt nicht WARUM der Subagent so vorgegangen ist, ob das Skill geholfen hat, oder was unklar war.

**Mit dieser Sektion**: Der Subagent reflektiert über die Tool-/Skill-Nutzung selbst. Output wird zur **Improvement-Signal-Quelle** für künftige Skill-Edits.

## Standard-Template

```markdown
**Zusätzliche Anforderung**: Am Ende, Sektion `## Skill-Self-Reflection`:
1. Welche Sektion des Skills hast du zuerst gelesen? (zeigt Skill-Struktur-Effizienz)
2. Welche Anweisungen hast du befolgt? Welche modifiziert/ignoriert und warum?
3. Was war hilfreich / unklar / fehlend?
4. [Optional] Hat dich das Skill vor einer "natürlichen falschen Empfehlung" bewahrt? Welcher?
```

## Variante für GREEN-Subagent in TDD-Promotion-Cycle

```markdown
**SKILL-DIREKTIVE**: Du hast Zugriff auf das Skill `<name>`. **Lade es ZUERST** via Skill-Tool und folge seinen Anweisungen.

**Zusätzliche Anforderung**: Am Ende, Sektion `## Skill-Self-Reflection`:
1. Welche Sektion des Skills hast du zuerst gelesen?
2. Hattest du Zugriff auf die Tools die das Skill voraussetzt? (Caller-Context-Check)
3. Welchen Modus hast du gewählt (Main-Pattern / Fallback)? Begründung.
4. Welche Anweisungen aus dem gewählten Modus hast du Punkt-für-Punkt umgesetzt?
5. Hat das Skill unklare Stellen / fehlende Anweisungen? Welche?
```

## Variante für RED-Subagent (ohne Skill)

```markdown
**CONSTRAINT**: Du darfst KEINEN Skill mit dem Namen `<name>` laden — der existiert noch nicht in deiner Umgebung.

**Wichtig für deine Berichterstattung**: Sei ehrlich was du gemacht hast und was nicht. Wenn du heuristisch vorgegangen bist, sag das. Wenn du dir bei einer Entscheidung unsicher warst, sag das.
```

(RED braucht KEINE Self-Reflection-Sektion — die Honesty-Direktive reicht. Self-Reflection wäre redundant weil RED ja kein Skill geladen hat.)

## Warum funktioniert das?

Subagents (Claude-Subagent, general-purpose) sind **selbst-reflexionsfähig** — wenn man sie explizit fragt. Ohne expliziten Prompt liefern sie default-mäßig nur Task-Output, nicht Meta-Feedback.

Die 3-4 Fragen sind nicht beliebig:
1. **„Welche Sektion zuerst gelesen?"** → zeigt ob Skill-Struktur effizient ist (entscheidende Info am Anfang?)
2. **„Welche Anweisungen modifiziert/ignoriert?"** → zeigt Skill-Realismus (Anweisungen die nicht ausführbar waren)
3. **„Hilfreich / unklar / fehlend?"** → liefert direkt 3 Verbesserungs-Listen
4. **„Vor welcher natürlichen falschen Empfehlung bewahrt?"** (optional) → zeigt Anti-Pattern-Value des Skills

## Wann anwenden

| Trigger | Anwenden? |
|---|---|
| Subagent dispatchen für Skill-TDD-Test (RED+GREEN) | ✅ ja — GREEN-Pfad |
| Subagent dispatchen für Tool-Evaluation („nutze MCP-X und sag mir wie es war") | ✅ ja |
| Subagent dispatchen für Skill-Promotion-Workflow (siehe skill-tdd-promotion-workflow) | ✅ ja — Cycle-2-Backlog-Quelle |
| Subagent dispatchen für Production-Task (Code-Fix, Code-Review, Feature) | ❌ nein — Output zählt, nicht Reflection |
| Subagent dispatchen für Time-Critical-Dispatch | ⚠️ skip — Self-Reflection addiert ~10-30% Token-Kosten |
| Bereits-bekannte Skill-Schwächen testen (gerichtetes A/B) | ⚠️ teilweise — direkter spezifischer Frage besser als allgemeine Reflection |

## Echte Output-Examples (Wolf-Cleanup-Day 26.05.2026)

### Output-Example 1: htmx-Skill GREEN-Test

Subagent-Self-Reflection lieferte:
> **Welches Anti-Pattern hat das Skill mich vermeiden lassen?**
> Den Default-Reflex `hx-trigger="load, every 60s"` direkt auf der `<section>` mit `hx-swap="outerHTML"`. Das ist genau das natürliche Pattern...

→ **Direkte Bestätigung dass Skill seinen Zweck erfüllt**. Ohne diese Frage hätte ich nur den Code-Output gesehen, nicht die kausale Bestätigung dass das Skill den Anti-Pattern verhindert hat.

### Output-Example 2: launchagent-Skill GREEN-Test

> **Vor welcher „natürlichen falschen Empfehlung" bewahrt?**
> Mindestens drei: 1. FDA für `/usr/bin/python3` setzen (SIP-Stub), 2. FDA für die Plist oder launchd granten (per-Executable), 3. `/opt/homebrew/bin/python3` im File-Picker (Symlink)...

→ Lieferte **explizite Liste von 3 Anti-Patterns** die ich solo nie so explizit dokumentiert hätte. Diese 3 sind jetzt im Skill als Diagnose-Tabelle hart-codiert.

### Output-Example 3: asyncpg-Skill GREEN-Test

> **Was war hilfreich / unklar / fehlend?**
> *Unklar:* Die Tabelle sagt nicht explizit was bei leerem Aggregate-Result passiert. Ich musste aus PG-Semantik herleiten: `COUNT` liefert immer `Decimal(0)`, `SUM`/`AVG` liefern `None`.

→ Cycle-2-Backlog-Item direkt identifiziert: „Empty-Set-Behavior-Spalte zur Lookup-Tabelle ergänzen". Solo hätte ich die Lücke nie bemerkt.

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| Subagent dispatchen ohne Self-Reflection für Skill-Test → nur Output ohne Meta-Feedback | Self-Reflection-Sektion ist Pflicht für skill-test-Dispatches |
| Self-Reflection-Fragen zu vage („was denkst du?") | Konkrete 3-4 strukturierte Fragen — Template oben |
| Self-Reflection bei jedem Subagent-Dispatch erzwingen (auch Production) | Nur bei evaluation/test, nicht bei reiner Execution |
| Subagent-Self-Reflection ignorieren („interessant aber nicht actionable") | Polish-Backlog-Items direkt in Skill-TDD-Verlauf übertragen |
| Self-Reflection-Section am Anfang des Prompts statt am Ende | Ende stellt sicher dass Subagent zuerst Task erledigt, dann reflektiert |

## TDD-Aufgabe für nächste Skill-Building-Session

1. **RED**: Subagent dispatchen für Skill-Test OHNE Self-Reflection-Sektion. Beobachten: liefert er Polish-Items proaktiv? Wahrscheinlich nein (nur Task-Output).
2. **GREEN**: Mit Skill: Caller bekommt expliziten Self-Reflection-Template-Vorschlag, baut ihn ein. Subagent liefert dann 3-5 strukturierte Polish-Items.
3. **REFACTOR**: Loophole „Aber für GROSSE Subagent-Tasks ist Self-Reflection 30% Token-Overhead" → Skill muss explizit machen wann skippen (Production-Tasks).
4. **Trigger-Phrasen**: „Subagent für skill-test", „TDD pressure-test", „evaluiere dieses Skill via Subagent" → wird Skill auto-getriggert?

## Querverweise

- `skill-tdd-promotion-workflow` — Hauptkonsument dieses Patterns (Cycle-2-Backlog-Quelle)
- `superpowers:writing-skills` — übergeordnetes Framework (das Skill verschärft die GREEN-Phase)
- `superpowers:dispatching-parallel-agents` — Pattern für mehrere parallele Self-Reflection-Subagents

## Real-World-Impact (Wolf-Cleanup-Day 26.05.2026)

5 Skill-Promotionen × 1 GREEN-Subagent each = 5 Self-Reflection-Outputs.

Geliefert: **13 Cycle-2-Backlog-Items** (siehe TDD-Verlauf-Sektionen pro Skill). Davon umgesetzt:
- 4 sofort als Polish-Commits (I1-I4 in ultimative-platform)
- 2 als M-Items (M2 Cleanup, M4 Doc-Drift)
- 7 dokumentiert als Cycle-2-Backlog in den Skill-Files

Ohne Self-Reflection-Pattern: ich hätte die Skills promotet, NICHT bemerkt dass die Lookup-Tabelle in asyncpg-Skill Empty-Set-Behavior fehlt, hätte cross-repo-Skill ohne API-Versioning-Hinweis released, etc. Das Pattern hat den **Reife-Stand der 5 Skills sichtbar gehoben** — vom „kompiliert" zum „dokumentiert + gehärtet".

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS)

- **RED-Subagent** (ohne Skill, Subagent-Prompt-Schreiben-Task für htmx-Skill-Test): Schrieb Standard-Task-Prompt mit eingebauter Trap (Anti-Pattern-Server-Response) + Skill-Direktive. Lieferformat mit Begründung + Loop-Free-Bestätigung. **Keine Self-Reflection-Sektion**. Selbsteinschätzung am Ende: „Self-Reflection wäre möglicherweise relevant gewesen" — erkannte Lücke retrospektiv aber baute sie nicht ein.
- **GREEN-Subagent** (mit Skill, gleicher Prompt): Nutzte explizit die GREEN-Variante-Template (Z. 30-39 des Skills). 5 Self-Reflection-Fragen am Ende eingebaut, adaptiert an Single-Pattern-Skill-Charakteristik (F3 umgeformt zu „Fix-Pattern Punkt-für-Punkt umgesetzt"). Anti-Pattern „Self-Reflection-Section am Anfang statt am Ende" explizit vermieden. Bait-Subtilitäts-Diskussion vorausschauend.
- **Verdict**: GREEN reproduzierte das Pattern exakt + ergänzte intelligente Anpassungen pro Skill-Typ. Skill PROMOTE.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **„Wie viel vom Test-Ziel im Prompt verraten?"-Heuristik-Tabelle** — Spektrum „blind testen" (kein Hint) bis „voll briefen" (alle Anti-Patterns nennen). Stark-natürliches-Anti-Pattern → blind. Subtiles Anti-Pattern → leichter Hint.
2. **Fragen-Adaption-Hinweis für Multi-Mode-Skills**: F3 muss je nach Skill-Charakteristik umgeformt werden (Single-Pattern vs. Main/Fallback-Split)
3. **Anti-Leak-Schutz-Pattern**: wie subtil sollte der Bait im Prompt sein? Realismus-vs-Subtilität-Trade-off explizit machen
