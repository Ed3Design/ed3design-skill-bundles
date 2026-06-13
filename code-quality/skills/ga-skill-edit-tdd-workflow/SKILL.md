---
name: ga-skill-edit-tdd-workflow
description: Use when editing or expanding an already-GA-promoted skill (suffix-less name, banner says PROMOTED) to add a new capability/class/feature. Different from `skill-tdd-promotion-workflow` which covers DRAFT→GA. This skill covers GA→GA+Capability — the failure mode is silent-rename-or-expand without RED-test for the new capability (Iron-Law violation). Trigger on phrases like "Skill erweitern um X", "neue Klasse zum existing Skill hinzufügen", "asyncpg-skill um JSONB erweitern", "GA-Skill umbenennen + Capability erweitern", "Skill-Rename mit Content-Expansion", "Cycle-2-Capability für promoted Skill". Do NOT load for new Skill from scratch (`superpowers:writing-skills`), for DRAFT→GA Promotion (`skill-tdd-promotion-workflow`), for minor edit ohne neue Capability (just edit), or when the target skill doesn't exist.
---

# ga-skill-edit-tdd-workflow (DRAFT — TDD-Promotion-Pending)

> ⚠️ **DRAFT 2026-05-29**: Pattern aus Wolf-Session 29.05.2026 nach Erweiterung von `asyncpg-decimal-test-shape` (GA seit 26.05.) um JSONB/UUID/INET-Klassen → Umbenennung zu `asyncpg-live-vs-mock-shape`. Iron-Law-Verstoß (silent rename ohne RED-Test für neue Capability) wurde durch Pre-Step-0-Check abgefangen. Pattern war ad-hoc gemacht, aber repeatable.

## Lifecycle-Position

```
[Idee] → CREATE (writing-skills) → -DRAFT
  ↓
PROMOTE (skill-tdd-promotion-workflow) → GA-Skill
  ↓
EDIT (DIESES Skill) → GA-Skill mit erweiterter Capability
```

`skill-tdd-promotion-workflow` ist NICHT für GA-Edits — das macht es explizit per „Do NOT load for editing GA-skills".  
`superpowers:writing-skills` (CREATE) ist nicht für Capability-Expansion auf existing GA — sonst wird existing Content fragmentiert.

Dieses Skill ist die fehlende Lifecycle-Stage.

## Pre-Step-0: Target-Verification (PFLICHT)

### Check A — Skill ist tatsächlich GA?

```bash
head -3 ~/.claude/skills/<SKILL-NAME>/SKILL.md | grep -E "name:.*-DRAFT|name:.*-STUB"
```

Wenn MATCH → Skill ist noch DRAFT → **falsches Skill verwendet** → STOP, `skill-tdd-promotion-workflow` zuerst.

### Check B — PROMOTED-Banner vorhanden?

```bash
grep -E "PROMOTED|✅" ~/.claude/skills/<SKILL-NAME>/SKILL.md | head -3
```

Wenn KEIN MATCH → Skill war nie explizit promoted (kein TDD-Verlauf dokumentiert) → STOP, erst writing-skills + skill-tdd-promotion-workflow.

### Check C — Neue Capability ist orthogonal zur existing?

Frage: addiert die Erweiterung eine NEUE Bug-Klasse / Pattern-Variante / Use-Case-Branch (ja → EDIT-Workflow legitim) ODER ist es nur Polish auf existing Content (nein → einfacher Edit, kein TDD nötig)?

| Erweiterung | Workflow |
|---|---|
| Neue Klasse / Bug-Pattern (z.B. JSONB neben Decimal) | EDIT-Workflow (dieses Skill) |
| Edge-Case-Doku zur existing Klasse | einfacher Edit (kein TDD) |
| Erweiterte Trigger-Phrasen ohne Content-Change | einfacher Edit |
| Major-Rename (semantische Verschiebung) | EDIT-Workflow + ggf. Old-Skill-Redirect |

## Pattern (8 Steps)

Pro GA-Skill-Expansion (nach Pre-Step-0-Pass):

1. **Original-Skill vollständig lesen** — verstehen was schon valididiert ist, was Klassen-/Sektion-Struktur ist
2. **Neuen erweiterten Skill als `-DRAFT` anlegen** unter neuem Namen (falls Rename) oder unter `<original-name>-DRAFT` (falls In-Place-Expansion staged) — Original bleibt unangetastet während TDD läuft
3. **Existing-Content unverändert übernehmen** + **NEUE Sektionen für neue Capability anhängen** — keine Re-Validation der existing Content nötig (war schon GA)
4. **RED + GREEN-Scenario designen** für die NEUE Capability — Bait der zum natürlichen Fehler in der neuen Klasse führt (NICHT die alte Klasse retesten — die ist validiert)
5. **Parallele Subagent-Dispatch** (Agent-Tool, `general-purpose`) — identischer Prompt-Stem, einziges Variable = Skill-Access. Verwende die `-DRAFT`-Datei für GREEN-Read-Tool-Pfad
6. **Analyse + Polish**: passt GREEN compliant für neue Capability? Self-Reflection-Findings ggf. inline einbauen (Iron-Law-konform: nur wenn ≤5min Polish, sonst Cycle-2-Backlog)
7. **DRAFT-Marker stripen** (name: + description: STUB-Prefix) + **PROMOTED-Banner Cycle-2-Update** (Datum + Verdict für NEUE Capability) + **TDD-Verlauf-Sektion erweitern** mit Cycle-N-Eintrag
8. **Directory-Rename + Old-Skill-Removal** (falls Rename) — Skills-Verzeichnis ist nicht git-versioniert, daher kein Commit-Step

## Konkretes Dispatch-Beispiel (Step 5)

So sieht RED+GREEN-Dispatch-Pair für GA-Edit aus (gekürzt aus 29.05.2026):

```python
# RED: ohne Skill, NEUE Capability scenario
Agent(
    subagent_type="general-purpose",
    description="RED-X <skill-shortname> <new-capability>",
    prompt="""
Du bist RED-Baseline (ohne Skill).

**CONSTRAINT**: KEIN Skill mit Namen `<old-name>` ODER `<new-name>` laden.

**Scenario**: <konkretes Mini-Problem das NUR die neue Capability triggert, nicht die alte>
<eingebaute Anti-Pattern-Bait, der ohne Skill natürlich auftritt>

⚠️ NO-FILE-WRITE: Markdown-Code-Blocks only, keine Dateien.

Output: Code + Begründung + Self-Reflection mit Unsicherheiten.
"""
)

# GREEN: mit erweitertem -DRAFT
Agent(
    subagent_type="general-purpose",
    description="GREEN-X <skill-shortname> <new-capability>",
    prompt="""
Du bist GREEN-Subagent.

**SKILL-DIREKTIVE**: Lies via Read-Tool: `/Users/<user>/.claude/skills/<NEW-NAME>-DRAFT/SKILL.md`.
Folge seinen Anweisungen für das Scenario.

**Scenario**: <IDENTISCH zu RED>

⚠️ NO-FILE-WRITE: Markdown-Code-Blocks only.

Skill-Self-Reflection-Sektion mit: erste gelesene Section / umgesetzt / vermiedene-Falsch-Empfehlung / Caller-Context-Check / hilfreich+fehlend.
"""
)
```

## Pre-Validated-Content-Skip

Iron-Law erlaubt Skip von Re-Validation **nur** für unveränderten Content:

- ✅ existing Klasse-A-Sektion unverändert → kein Re-RED-Test für Klasse A
- ✅ Cycle-1-TDD-Verlauf-Eintrag bleibt → wird durch Cycle-2 ergänzt, nicht ersetzt
- ❌ Klasse-A-Sektion umstrukturiert/neu-formuliert → Re-RED-Test für Klasse A nötig
- ❌ Default-Werte geändert in existing Sektion → Re-RED-Test für alle betroffenen Klassen

Faustregel: wenn du existing Sektion editierst (nicht nur anhängst), wird sie zur „neuen Capability" → Re-TDD.

## Rename-Strategien

Wenn EDIT von Capability-Expansion auch Rename involviert (z.B. `asyncpg-decimal-test-shape` → `asyncpg-live-vs-mock-shape`):

### Option A — Hard-Rename + Delete-Old (Wolf-Pattern 29.05.)

- Neuer Skill unter neuem Namen
- Alter Skill-Directory komplett entfernt
- **Vorteil**: clean, kein Duplikat-Auto-Discovery
- **Nachteil**: Trigger-Phrasen aus alter Beschreibung müssen in neuer description abgedeckt sein (sonst Discovery-Lücke)

### Option B — Old-Skill mit Redirect

- Alter Skill-Directory bleibt
- Content: einzige Sektion „⚠️ This skill has been superseded by `<new-name>`. See there."
- Description bleibt mit alten Triggers, ergänzt um „use new-name instead"
- **Vorteil**: backward-compatible für Trigger-Phrase-Discovery
- **Nachteil**: 2 Skills laden bei Trigger-Match

**Wolf-Default 29.05.**: Option A (Hard-Rename). Trigger-Phrasen wurden in neue description konsolidiert.

## Polish-vs-Promote-Decision (analog skill-tdd-promotion-workflow)

| Item-Typ | Action |
|---|---|
| Sub-Skill-essential für neue Capability (z.B. unklarer Trigger) | jetzt einbauen vor PROMOTE |
| Edge-Case-Doku für neue Capability (≤5min) | jetzt einbauen |
| Pattern-Erweiterung („wäre noch nützlich") | Cycle-N-Backlog |
| Refactor an existing Content (≥5min, orthogonal zur Capability) | separate Session |

## Anti-Patterns

| Anti-Pattern | Korrekt |
|---|---|
| Silent rename + expand ohne RED-Test für neue Capability | Iron-Law-Verstoß; RED-Test ist Pflicht für jede neue Klasse |
| Re-RED-Test für existing validierten Content | Iron-Law-Pflicht ist failing-test-first; unveränderter Content braucht das nicht |
| Pre-Step-0 skippen weil „Ich weiß doch dass es GA ist" | 1-Sekunde-Check, falsche Annahme kostet 30min Re-Work |
| Old-Skill-Directory vergessen zu entfernen bei Hard-Rename | Auto-Discovery findet beide → User-Confusion |
| PROMOTED-Banner nicht ge-Cycle-2-update'd | Spätere Reviewer denken Skill ist GA-since-Cycle-1, sehen aber neue Klassen ohne TDD-Backing |
| NEUE Capability ohne TDD-Verlauf-Cycle-N-Entry | Cycle-Tracking ist Voraussetzung für künftige Cycle-3+-Edits |
| Wolf-Direktive „expand X" als CREATE-Workflow interpretieren | Wenn X bereits GA-Skill ist, ist es EDIT, nicht CREATE |

## Querverweise

- `superpowers:writing-skills` — CREATE-Stage (vor PROMOTE)
- `skill-tdd-promotion-workflow` — PROMOTE-Stage (DRAFT → GA)
- `superpowers:dispatching-parallel-agents` — Mechanik für Step 5
- `superpowers:test-driven-development` — Iron-Law-Basis
- `subagent-self-reflection-prompt-pattern` — Polish-Item-Quelle

## TDD-Aufgabe für künftige Promotion

Vor GA-Promotion dieses Skills selbst:
1. RED+GREEN-Pressure-Test mit Scenario: „User sagt 'erweitere asyncpg-decimal-test-shape um JSONB'"
2. RED ohne Skill: würde vermutlich `superpowers:writing-skills` laden oder silent renamen
3. GREEN mit DIESEM Skill: lädt Pre-Step-0 Check A/B/C, identifiziert EDIT-Mode, dispatcht RED+GREEN für JSONB-Capability, rename mit Option A
4. Erwartung: GREEN strukturell sauberer, expliziter im Workflow-Pick

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-29 (DRAFT-Phase)

Skeleton aus Wolf-Session 29.05. Echte TDD-Pressure-Test pending. Pattern ad-hoc angewandt heute:
- Original `asyncpg-decimal-test-shape` (GA seit 26.05.) gelesen
- Erweiterung als `asyncpg-live-vs-mock-shape-DRAFT` angelegt mit 5 Klassen (A-E)
- RED+GREEN für Klasse B (JSONB) — PASS
- Inline-Polish für Symptom-Klarheit (5 Access-Pattern-Mapping)
- Hard-Rename Option A: Directory `asyncpg-decimal-test-shape` entfernt, `-DRAFT` → final-Name
- PROMOTED-Banner Cycle-2-Update mit Datum 2026-05-29

Resultat: Skill mit 5 Bug-Klassen statt 1, Cycle-1-Decimal-Validation erhalten + Cycle-2-JSONB-Validation hinzugefügt. Saubere Lifecycle-Progression.
