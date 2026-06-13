---
name: plan-execution-stack-mode-precheck
description: Use as Pre-Step-0 of `executing-plans` / `subagent-driven-development` / inline-plan-execution when the plan contains `docker compose exec`, SSH-Commands oder andere Stack-Interaction-Steps. The check distinguishes (a) local-runnable-stack vs (b) remote-only-stack vs (c) hybrid-mode (code-local + live-remote). Prevents mid-execution-stop-gates when the plan implicitly assumes „docker compose works here" but secrets/.env.prod, env-files, or services are missing locally. Trigger on phrases like "Plan ausführen", "executing the plan", "subagent-driven execution start", "docker compose exec in plan steps", "deploy stack vs dev stack", "swatserver vs lokal" mid-plan. Do NOT load for plans without stack-interaction (pure-function-only-tasks), for plans where stack-mode ist explizit dokumentiert, or for the initial plan-writing phase (writing-plans hat seinen eigenen Self-Review).
---

# plan-execution-stack-mode-precheck (DRAFT — TDD-Promotion-Pending)

> ⚠️ **DRAFT 2026-05-29**: Pattern aus Wolf-Session 29.05.2026 Phase-Z.1-Execution. Z.1-Plan hatte `docker compose exec`-Steps die implizit „local stack running" annahmen. Lokal fehlten `secrets/.env.prod` UND der Docker-daemon war off → 2-Step-Stop-Gate mid-Execution gekostet ~20min Session-Time + Mode-Pivot zu Hybrid. Hätte vor Z.1-Start 5min Pre-Check verhindert.

## Lifecycle-Position

Pre-Step für jeden Plan-Execution-Workflow:

```
[Plan exists] → writing-plans Self-Review ✓
              ↓
[Execution starting] → DIESES Skill (Pre-Step-0 Stack-Mode-Check)
              ↓
[Mode klar] → executing-plans / subagent-driven-development / inline
```

## Die drei Stack-Modes

| Mode | Beschreibung | Plan-Step-Auswirkung |
|---|---|---|
| **Local-Runnable** | Compose-File + alle env-Files + Services lokal lauffähig | alle `docker compose exec` als-ist durchziehen |
| **Remote-Only** | Stack läuft NUR auf Server (swatserver / Cloud) | alle `docker compose exec` via SSH ausführen ODER deferred |
| **Hybrid** | Code lokal entwickel-bar, Live-Verify nur remote | Code-Steps lokal, Live-Verify-Steps als „pending remote-deploy" markieren |

## Pattern (4 Steps)

### Step 1: Compose-File-Inspect (10 sec)

```bash
# Finde docker-compose.yml / compose.yml
find . -maxdepth 3 -name "compose.yml" -o -name "docker-compose.yml" 2>/dev/null | head -3

# Inspect env-File-Anforderungen
grep -E "env_file|secrets|env_var" $(find . -maxdepth 3 -name "compose.yml" -o -name "docker-compose.yml" | head -1)
```

Output zeigt welche `.env`-/secrets-Files das Compose-Setup voraussetzt.

### Step 2: Env-Files-Existenz-Check (5 sec)

```bash
# Für jede vom Compose referenzierte env-Datei
for f in .env .env.prod secrets/.env.prod docker/.env; do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ $f MISSING"
done
```

Wenn eine MUST-EXIST-File fehlt → Mode ist NICHT „Local-Runnable" für diese Stack-Operation.

### Step 3: Daemon + Services Sanity (15 sec)

```bash
# Docker daemon up?
docker info >/dev/null 2>&1 && echo "✓ daemon up" || echo "✗ daemon down (open -a Docker auf Mac)"

# Services running?
docker compose -f <compose-file> ps 2>&1 | head -5
```

Wenn daemon down ODER `ps` returns empty → Stack ist nicht ready. Plan-Steps die `exec` brauchen werden scheitern.

### Step 4: Mode-Verdict + Plan-Annotation

Basierend auf Step 1-3:

- **Local-Runnable**: weiter mit Plan as-is. Optional Stack starten (`docker compose up -d`).
- **Remote-Only**: Plan-Step für Plan-Step prüfen — was MUSS lokal laufen (Code-Edit, pytest-Mock-Tests), was MUSS remote (DB-Migration-Live, Live-Backfill, Live-Backtest)?
- **Hybrid**: explizite Aufteilung in Daily-Note dokumentieren:
  - Lokal heute: alle Code-Tasks + Pure-Function-Tests + Mock-Integration-Tests
  - Remote morgen: Live-DB-Migration, Live-Backfill, Live-Backtest, 24h-Cycle-Verify

## Annotation-Pattern für Plan-Steps

Bei jeder `docker compose exec`-Zeile im Plan:

```markdown
- [ ] **Step N: <Action>**

Run:
```bash
docker compose exec app python -m scripts.X
```
**Stack-Mode**: LOCAL-ONLY / REMOTE-ONLY / HYBRID-pending-remote
```

Im Hybrid-Mode: alle REMOTE-pending-Steps in Daily-Note Carry-Over-Block, NICHT als „DONE" markieren bevor remote-execution.

## 24h-Cycle-vor-closed-as-done — Maxime-Anwendung

Wolf-Maxime: „Code-fertig ≠ Task-DONE bis 24h-Live-Cycle das Erfolgs-Kriterium bestätigt."

Bei Hybrid-Mode wird das mechanisch wichtig:
- Lokal-Tests grün ≠ Task-DONE
- DONE-Marker erst NACH erfolgreichem swatserver-Live-Run + 24h-Cycle-Verify

In Roadmap: explizite Trennung „Code-Complete" vs „Live-Verified".

## Anti-Patterns

| Anti-Pattern | Korrekt |
|---|---|
| `executing-plans` direkt starten ohne Stack-Mode-Check | Pre-Step-0 mit 30sec-Total dauert weniger als 5-10min Mid-Execution-Stop |
| Stack-Mode-Pivot mitten in Subagent-Driven-Loop | Pivot KOSTET Subagent-Overhead — vor erstem Subagent-Dispatch klären |
| „DONE"-Marker für Code-Complete-aber-nicht-Live-Verified | Wolf-Maxime: 24h-Cycle vor closed-as-done. Hybrid = „Code-Complete, pending Live-Verify" |
| Plan-Schreibung ohne Stack-Mode-Annotation | writing-plans Self-Review sollte das prüfen (Memory-Item für Plan-Author) |
| Docker.app-Start mid-Execution | Pre-Step-0 startet Daemon parallel zu Compose-Inspect (10sec-Parallel-Save) |

## Querverweise

- `superpowers:executing-plans` — Parent-Workflow (dieses Skill ist Pre-Step-0)
- `superpowers:subagent-driven-development` — Parent-Workflow (selbiges)
- `superpowers:writing-plans` — Plan-Schreibung sollte Stack-Mode-Annotation enthalten (Cycle-2-Backlog für writing-plans-Skill)
- `swatserver-fastapi-iteration` — wenn Stack-Mode = Remote-Only, dieses Skill für Live-Deploy
- `tailscale-multi-account-diagnosis` — wenn Remote-Verbindung kaputt

## Real-World-Impact (heute 2026-05-29)

- **Z.1-Execution-Start** ohne Pre-Check → Docker daemon down (10sec-Stop) + `secrets/.env.prod` fehlt (15min Mode-Pivot)
- **Hätte mit Pre-Check** in 30sec aufgedeckt → Hybrid-Mode-Decision VOR erstem Code-Edit
- **Token-Cost**: ~30k Mid-Execution-Recovery wegen Mode-Pivot — gespart durch Pre-Step-0
- **Strukturelle Lehre**: Plan-Z.1 selbst war nicht „falsch", aber die `docker compose exec`-Steps brauchten explizite Stack-Mode-Annotation. → Memory-Item für `writing-plans`-Sub-Step.

## TDD-Aufgabe für künftige Promotion

Vor GA-Promotion dieses Skills:

1. **RED-Scenario**: User sagt „starte execution des Plans X" (Plan enthält `docker compose exec`, Stack ist remote-only) — RED ohne Skill startet vermutlich Plan-Step 1, scheitert an docker-Command
2. **GREEN-Scenario**: gleicher Prompt, mit DIESEM Skill — GREEN macht Pre-Step-0 Stack-Mode-Check, identifiziert Remote-Only, schlägt Hybrid-Mode vor
3. **Expected RED-Failure-Mode**: 5-10min Mid-Execution-Discovery vs GREEN's 30sec Pre-Check
4. **Verdict-Kriterium**: GREEN präsentiert Mode-Verdict + Plan-Annotation BEVOR Code-Action

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-29 (DRAFT-Phase)

Skeleton aus Wolf-Phase-Z.1-Execution-Session. Echte TDD-Pressure-Test pending. Pattern ad-hoc heute angewandt (nach Auftreten des Stop-Gates):
- Docker.app-Start während Working-Tree-Cleanup parallelisiert
- `secrets/.env.prod` Existenz-Check enthüllt Remote-Only-Stack-Realität
- Hybrid-Mode-Decision via AskUserQuestion (Wolf wählte „Continue durchziehen" → Hybrid)
- Plan-Steps in „lokal heute" vs „swatserver morgen" aufgeteilt in Daily-Note Block 5

Resultat: Phase-Z.1 9-Tasks Code-Complete trotz Stack-Mode-Mismatch — durch ad-hoc-Hybrid statt Plan-Mid-Stop. Skill-Existenz hätte den Pivot-Detour gespart.
