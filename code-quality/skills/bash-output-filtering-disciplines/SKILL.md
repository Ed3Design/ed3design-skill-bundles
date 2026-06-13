---
name: bash-output-filtering-disciplines
description: Use BEFORE running any Bash command that could produce more than ~50 lines of stdout: `docker logs`, `docker ps -a` (long format), `git log` (full history), `find` (deep tree), `ps aux`, `psql -c "SELECT * FROM ..."`, `cat large.log`, `ls -la` (deep dirs), `journalctl`, `dmesg`, `kubectl logs`, `du -a`. STOP and apply head/tail/grep/wc/jq/awk/sed pre-filters in the SAME command pipeline — never let raw output flow into the conversation context. Every line above the relevant data is wasted Tokens that accumulate over a session (heute morgen ~50k Tokens für Container-Status alleine). Trigger phrases like „docker logs Container X", „git log angucken", „find Files mit Pattern", „ps aux", „journalctl", „SELECT * FROM tabelle", „komplette Logs durchsuchen", „was alles im Verzeichnis liegt", „ls auf großem Folder", „warum ist meine Session-Token-Verbrauch hoch". Do NOT apply when the user EXPLICITLY asked for full output („zeig mir den kompletten Output", „bitte unfiltered"), for commands that are inherently small (`whoami`, `pwd`, `uname -a`, `date`), for one-shot value-extractions (`echo $VAR`, `grep -m1 PATTERN file`), or when piping to a file (`cmd > /tmp/full.txt` — file-write is fine, follow-up Read can be filtered). Encodes Wolf-Token-Optimierung-Pain from 11.06.2026: Vormittag-Session ~30k Tokens nur Bash-Tool-Outputs (Cockpit + docker ps + docker logs ohne tail), Brain-Dump-Item „kritische Analyse der Token-Nutzung" als Wolf-Maxime.

---

# Bash Output Filtering Disciplines

> ✅ **PROMOTED 2026-06-12** via TDD-Cycle. RED-Subagent reflektierte selbst „mein Default ist deutlich nicht token-effizient — 50× mehr Tokens als nötig". GREEN-Subagent erreichte mit Skill **~98% Saving** (~500 Tokens statt ~50k) via 1 SSH-Call mit server-side for-loop statt 5× sequenzielle SSH-Calls.

## Overview

**Pain-Anker**: Wolf-Token-Optimierungs-Session 11.06.2026 — ein einziger Health-Check-Sweep verbrennt ~15-20k Tokens nur durch unfilterte Bash-Outputs (Container-Listen, Logs ohne tail, SELECT * statt count, find ohne head). Über 30 Trading-Sessions/Monat ≈ ~500k Tokens reine Boilerplate.

**Core-Disziplin**: Filter **in derselben Command-Pipeline**, nicht „ich filtere mental nach dem Lesen". Sobald Output im Conversation-Context ist, sind die Tokens verbraucht — egal ob du es liest oder nicht.

## When to Trigger

✅ **JA — Filter-first:**
- Command könnte > 50 Output-Lines produzieren
- Command hat `*`-Wildcard oder Tree-Recursion (`find /`, `ls -laR`)
- DB-Query ohne `LIMIT`, `count(*)` oder `EXPLAIN`
- Log-Reading ohne `--tail` / `--since`
- Process-Listing ohne `grep PROCESS_NAME`
- File-Listing in unbekanntem (potentiell großem) Verzeichnis

❌ **NEIN — voll OK:**
- User sagte explizit „kompletter Output bitte"
- One-shot Value-Extract (`whoami`, `date`, `pwd`, `echo $VAR`)
- Tool-Output ist bekannt-klein (< 50 Lines garantiert)
- Pipe-to-File für später (`cmd > /tmp/x.txt` → Read mit `offset+limit` danach)

## Pattern-Katalog

### 1. `docker logs` — IMMER mit `--tail` ODER `--since`

```bash
# ❌ schlimm: alle Logs seit Container-Start
docker logs ultimative-trader

# ✅ gut: letzte 50 Zeilen
docker logs --tail 50 ultimative-trader

# ✅ besser: zeitlich begrenzt
docker logs --since 30m ultimative-trader

# ✅ am besten: + grep für relevant
docker logs --since 1h ultimative-trader 2>&1 | grep -iE "error|warning" | tail -20
```

### 2. `docker ps` — Format einschränken

```bash
# ❌ schlimm: Full-Format mit viel Whitespace
docker ps -a

# ✅ gut: nur Name + Status
docker ps --format "table {{.Names}}\t{{.Status}}"

# ✅ besser für 1-Line-Health-Check:
docker ps --format "{{.Names}}: {{.Status}}" | grep -v healthy
# → zeigt NUR unhealthy/restarting Container
```

### 3. `git log` — IMMER mit `-n N` oder `--oneline`

```bash
# ❌ schlimm: ganze Historie mit Vollformat
git log

# ✅ gut: 10 letzte Commits einzeilig
git log --oneline -n 10

# ✅ besser: nur SHA + Subject + Datum
git log --pretty=format:"%h %ad %s" --date=short -n 20
```

### 4. `find` — IMMER mit Output-Cap

```bash
# ❌ schlimm: kann tausende Files dumpen
find /Users/w/Projects -name "*.py"

# ✅ gut: max 20 Files
find /Users/w/Projects -name "*.py" | head -20

# ✅ besser: nur Count
find /Users/w/Projects -name "*.py" | wc -l

# ✅ am besten: Use Glob-Tool für Vault/Repo-Searches (Token-cheaper als find+pipe)
```

### 5. `psql` — `LIMIT`, `count(*)`, `--csv`

```bash
# ❌ schlimm: könnte 10.000 Rows zurückgeben
psql -c "SELECT * FROM v3_trades"

# ✅ gut: LIMIT + relevante Spalten
psql -c "SELECT id, symbol, status FROM v3_trades ORDER BY id DESC LIMIT 10"

# ✅ besser: Aggregat statt Rows
psql -c "SELECT count(*), status FROM v3_trades GROUP BY status"

# ✅ Output-Format für Subagent-Verarbeitung
psql --csv -c "SELECT id, symbol FROM v3_trades LIMIT 10"
```

### 6. `ps aux` — IMMER mit `grep`

```bash
# ❌ schlimm: alle Prozesse des Systems
ps aux

# ✅ gut: nur der Prozess der interessiert
ps aux | grep -i python | grep -v grep | head -5
```

### 7. `journalctl` / `dmesg` — Zeit-Filter

```bash
# ❌ schlimm: alle Boot-Logs
journalctl

# ✅ gut: nur letzte Stunde, nur Errors
journalctl --since "1 hour ago" -p err --no-pager | tail -50
```

### 8. `cat large.log` / Full-File-Read

```bash
# ❌ schlimm: dumpt komplette Log-Datei in Context
cat /var/log/app.log

# ✅ gut: nur Ende
tail -100 /var/log/app.log

# ✅ besser: nur relevante Lines
tail -1000 /var/log/app.log | grep -iE "error|critical"

# ✅ für Read-Tool: offset + limit nutzen
# Read file_path="/var/log/app.log" offset=5000 limit=200
```

### 9. JSON-Output — `jq -c` für one-line

```bash
# ❌ schlimm: pretty-printed JSON mit jeder Zeile expanded
curl http://api/data

# ✅ gut: compact one-line per Object
curl -s http://api/data | jq -c '.[]' | head -20

# ✅ besser: nur relevante Felder
curl -s http://api/data | jq -c '.[] | {id, status}' | head -20
```

### 10. `ls -la` auf großen Folders

```bash
# ❌ schlimm: alles
ls -la ~/.claude/skills/

# ✅ gut: nur Verzeichnis-Count
ls ~/.claude/skills/ | wc -l

# ✅ besser: Namen einspaltig
ls ~/.claude/skills/ | head -20
```

### 11. `du -sh` statt `du -a`

```bash
# ❌ schlimm: jeden File einzeln
du -a ~/Downloads

# ✅ gut: nur Summary
du -sh ~/Downloads

# ✅ Top-10 größte Dirs
du -sh ~/Downloads/* | sort -rh | head -10
```

### 12. `wc -l` als Vorab-Probe

Wenn unklar ob Output groß ist:

```bash
# Probe zuerst (ein Integer-Output)
cmd | wc -l
# → wenn < 50: cmd ohne Filter
# → wenn > 50: Filter dazu
```

## Heuristik: Wann welcher Filter

| Output-Typ | Default-Filter | Begründung |
|---|---|---|
| Logs (zeitlich) | `--tail 50` oder `--since 30m` | Recent ist meistens relevanter als Historie |
| Logs (Pattern) | `grep -iE "error\|warn" \| tail -20` | Pre-Filter ERROR-Klasse |
| Listen (Files, Container, Prozesse) | `\| head -20` | Sample reicht für Übersicht |
| Listen (Count gefragt) | `\| wc -l` | Nur die Zahl |
| Tables (DB) | `LIMIT 10` oder `count(*)` | Volldumps sind selten produktiv |
| JSON-Streams | `jq -c '.field' \| head -20` | Compact + relevant |
| Find/Search | `\| head -20` | Erste Treffer reichen, sonst Pattern verfeinern |

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| `cmd > /tmp/x.txt && cat /tmp/x.txt` | File-Write OK, danach `Read offset+limit` oder `tail/head` direkt |
| Re-Run desselben Commands „weil ich's nochmal sehen will" | Output ist in History — recall, nicht re-run |
| `docker logs container \| less` | `less` macht nichts für Token-Context (kein interactive Reader im Bash-Tool) |
| `find / -name "X"` ohne Cap | IMMER `\| head`, oder besser Glob-Tool |
| `psql -c "SELECT *"` | `LIMIT` oder `count` — sonst Memory + Token-Burn |
| Verlassen auf User-Confirm „passt, kannst du die letzten 10 zeigen?" | Pre-Filtern, dann ggf. „weitere bei Bedarf"-Note |
| Fünf SSH+docker exec-Calls statt 1 HTTP-Aggregator-Call | wenn MCP/Health-Aggregator existiert: nutzen statt SSH-Chain |
| Output `2>&1` ohne Stderr-Need | Stderr nur dann mergen wenn man Errors mitlesen will |

## Cost-of-Skipping

Empirie aus Wolf-Sessions 06/2026 (geschätzt):

| Operation | ohne Skill (typisch) | mit Skill | Saving |
|---|---|---|---|
| Container-Health-Check (5 Container) | ~3-5k (`docker ps -a` + 5× `docker inspect`) | ~200 (`docker ps --format "..."`) | **~95%** |
| Recent-Error-Sweep | ~5-8k (`docker logs` ungefiltert × N Container) | ~500-800 (`docker logs --since 30m \| grep ERROR \| tail -20`) | **~90%** |
| Git-Log-Review pro Repo | ~2-3k | ~200 (`git log --oneline -n 10`) | **~93%** |
| Find-Suche im großen Tree | ~3-10k | ~300 (`\| head -20` oder Glob-Tool) | **~95%** |
| DB-Trade-Statistik | ~800-2000 (`SELECT *`) | ~50-100 (`count(*)`) | **~95%** |

**Hochrechnung**: 30 Trading-Sessions/Monat × 3-5 dieser Operations pro Session × 5k saved = **~450-750k Tokens/Monat strukturell vermieden**. Bei Fable-Pay-per-Use (ab 23.06.) ≈ $5-8/Monat saved. Bei Opus im Plan: bewahrt Plan-Limit vor Boilerplate-Burn.

## Connection to other Skills

- **`db-telemetry-primary-docker-logs-secondary`** (GA): Skill predigt Vault-DB-Telemetry **statt** Docker-Logs als primary. Dieses Skill ist die ergänzende Disziplin **wenn** Docker-Logs gebraucht werden (secondary).
- **`Sub-Agent-Modell-Matrix`** (Vault-Notiz): Bulk-Smoketest-Subagents nutzen Haiku — wenn Bash-Output groß bleibt, multipliziert sich der Token-Cost pro Subagent. Filter-Disziplin reduziert Subagent-Cost ebenfalls.
- **`reporting-artefact-detection-before-claiming-anomaly`** (GA): bevor Anomalie behauptet wird, prüfe ob die Bash-Output-Sample groß genug war (Anti-Pattern: aus 5 grep-Treffern Anomalie ableiten).
- **`code-review-chunk-dispatch`** (GA): Code-Review-Subagents geben Output zurück — wenn jeder Subagent Bash-Output rohgreift, mehrfacher Token-Burn.
- **`enum-known-values-via-insert-grep`** (GA): wenn dieser Skill `grep -rn ... | head -20` macht (statt all), bleibt sein eigener Cost klein.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS — 98% Token-Saving validiert)

- **RED-Subagent** (ohne Skill, Scenario: Health-Check 5 ultimative-Container auf swatserver via SSH): Schrieb 5 sequenzielle SSH-Calls (`docker logs --since 30m | grep error` ohne `| head`, `--tail 100` „falls Wolf nachfragt" Reflex), schätzte 6k-28k Token-Verbrauch. Self-Assessment: „deutlich nicht token-effizient — 20-50× mehr Tokens als der effiziente Approach". Hat selbst den korrekten Approach formuliert („`for c in ...; do ... done` in EINEM SSH-Call") — aber **nur als nachträgliche Reflexion**, nicht als Default.

- **GREEN-Subagent** (mit Skill via Read-Tool, gleiche Aufgabe): 1 SSH-Call mit server-side `for`-Loop, `docker ps --format "{{.Names}}: {{.Status}}"`, `--since 30m | grep -iE "error|critical" | tail -5`. Token-Verbrauch ~500 Tokens vs ~50k naiv = **~98% Saving empirisch**. Identifizierte Skill-Lücke: SSH-Multiplex-Pattern nicht explizit dokumentiert (aus Anti-Pattern abgeleitet).

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **SSH-Multiplex-Pattern als Item #13** — `ssh host 'for ...; do ...; done'` statt 5× `ssh host '...'`. SSH-Connection-Setup-Cost vermeiden
2. **`docker compose ps`-Variante** als Alternative zu `docker ps --format`
3. **Health-Check via curl**: `curl -sf http://host:port/healthz` wenn Container `/healthz` exposed — billiger als Logs lesen. Cross-Link zu `traefik-internal-route-probe`
4. **Container-Set-Prefix-Filter** wenn `docker ps` >50 Container zeigt (Swarm-Node-Edge-Case)

## Quell-Triggers

- Wolf-Token-Optimierung Sprint 1 Item 3 (11.06.2026) — Brain-Dump-Item „kritische Analyse der Token-Nutzung"
- Empirie aus Vormittag-Session 11.06.: ~30k Tokens nur Bash-Outputs (Cockpit + Container-Status + docker logs)
- Pattern-Sammlung aus 145-Session-Workflow-Review (`AI & Machine Learning.md` Lessons-Sektion)

---

_Erstellt 2026-06-11 ~Abend nach Sub-Agent-Modell-Matrix (Sprint 1 Item 2 erledigt). Status DRAFT, Promotion via `skill-tdd-promotion-workflow` als Backlog-Item Sprint 3._
