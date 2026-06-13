---
name: roadmap-phase-execution-verify-first
description: Captures the pattern from Wolf-Vault 25.05.2026 Phase-A-Execution-Session: when executing a Roadmap-Phase from an Obsidian-Vault that was designed days/weeks ago AND a previous session may have prepared draft artifacts (Service-Maps, status-files, execution-guides), verify each Item against current reality (DB queries, docker inspect, systemctl, filesystem) BEFORE applying changes. Find drift in pre-existing files; document discoveries that turn a routine item into an issue; never check a roadmap-item as done just because the roadmap said so. Trigger on phrases like "Phase X implementieren", "Roadmap-Item umsetzen", "Phase A der … Konsolidierung implementieren", "Item Y aus der Roadmap", "die Phase aus dem Vault ausführen". Do NOT load for fresh roadmap design (use brain-dump-to-phased-roadmap), for executing a freshly-written task list with no Vault-history, or for non-Wolf-Vault roadmaps.
---

# Roadmap-Phase-Execution: Verify-Before-Touch

> ✅ **PROMOTED 2026-05-27**: TDD-Pressure-Test bestanden. RED-Subagent zeigte vernünftigen verify-first-Vorschlag (Daily Notes scannen, DB-Query, Pi-Status). GREEN-Subagent ging einen Schritt weiter: las die EXISTIERENDE Phase-A-Roadmap im Vault und entdeckte **Phase A ist bereits abgeschlossen** (Audit-Log + Commit-Hashes vorhanden) → Drift-Tabelle gezeigt, 3-Szenarien-Sanity-Frage statt Häkchen-Setzen, Phase 3 (Execution) explizit nicht gestartet. Skill verhinderte False-Positive-„done"-Setzung. Cycle-2-Backlog: Fallback-Mode No-SSH-Subagent, „Phase bereits done"-Anti-Pattern-Zeile, Trust-Boundary-Check.

## Overview

Bei der Umsetzung einer Roadmap-Phase aus Wolfs Obsidian-Vault (Phase A/B/C einer Konsolidierungs-Roadmap, oder ähnliche Multi-Item-Phasen) ist die Default-Reaktion „häkchen-für-häkchen abarbeiten" gefährlich. Drei Quellen für stille Drift:

1. **Die Roadmap selbst** wurde Tage/Wochen früher geschrieben und enthält Aussagen, die nicht mehr stimmen (z.B. „3 offene Trades" — heute 15)
2. **Vorgänger-Sessions haben bereits Artefakte vorbereitet** (Service-Map, Status-Files, Execution-Guides) — oft mit Erinnerungs-Werten statt Messungen
3. **Items können bereits faktisch erledigt sein** (z.B. „Pi-Services disablen" — Pi war schon clean), aber an die Bedingung „X bestätigt" geknüpft, die ihrerseits nicht stimmt

**Kern-Prinzip**: jedes Item zuerst gegen Realität verifizieren, dann die richtige Aktion ausführen — die kann „update", „verify-only", „discovery-doc statt häkchen" oder „original-action" sein.

## When to use

Trigger-Phrasen:
- „Phase A/B/C der … implementieren"
- „Roadmap-Item umsetzen"
- „Die Phase aus dem Vault ausführen"
- „Item Y aus der Roadmap"
- „Roadmap … X implementieren"

Konkrete Signale:
- Roadmap-Datei liegt in `02 Projekte/.../Roadmap-*.md` mit Items A1-A6 / B1-B5 etc.
- Datum der Roadmap ist > 3 Tage alt
- Im selben Ordner gibt es bereits Artefakte wie `*-Service-Map.md`, `*-status.md`, `*-Execution-Guide.md`
- User-Trigger ist „Phase X umsetzen", nicht „Phase X neu designen"

## When NOT to use

- **Fresh Roadmap-Design**: Brain-Dump zur Roadmap konsolidieren → `brain-dump-to-phased-roadmap`
- **Freshly-written task list** (gleicher Tag, gleiche Session, keine Vorgänger-Artefakte): einfach abarbeiten, kein Verify-Overhead nötig
- **Non-Vault-Roadmap**: Wenn die Quelle GitHub-Issues, Linear, Jira oder ein anderes Tool ist, nicht Wolfs Obsidian-Vault, gelten andere Drift-Pattern (dort triggern primär `gsd:gsd-execute-phase` oder ähnliche)

## Die 3-Phasen-Schleife

### Phase 1 — Reality-Inventur (vor dem ersten Edit)

Bevor irgendeine Datei angefasst wird, ein paar Min in Verifikations-Queries investieren:

| Was die Roadmap behauptet | Wo es zu verifizieren ist |
|---|---|
| Container/Services laufen auf Host X | `ssh user@host "docker ps"` + `systemctl list-timers --all` |
| Datenbank hat N Zeilen / Trades / Records | `docker exec <db> psql -U <user> -d <db> -c "SELECT count(*)..."` |
| Hardware-Inventar (CPU, RAM, Disk, Cores) | `ssh user@host "nproc && free -m && df -BG /"` |
| Eine andere Maschine ist Warm-Standby/disabled | `ssh user@other-host "systemctl list-units --state=enabled \| grep ..."` |
| Backup-Coverage vorhanden | `cat /etc/restic/.../*.sh` + `ls /srv/backups-staging/` + Snapshot-Liste |
| Vorgänger-Status-File ist aktuell | Inhalt der Datei vs. obige Realitäts-Quellen vergleichen |

**Output dieser Phase**: eine kleine „Drift-Tabelle" — Roadmap-Behauptung vs. Realität, in Bullet-Form. Diese Tabelle ist die Entscheidungs-Basis für alles Folgende.

### Phase 2 — Sequencing & Sanity-Check beim User

Bevor mit Schreiben begonnen wird:

1. **Drift-Tabelle dem User zeigen** (insbesondere wenn 2+ Items drift-betroffen sind)
2. **Sequencing vorschlagen**: erst dokumentieren (drift-Reparatur) → dann verifizieren → dann verändern
3. **Scope-Fragen klären** wenn Roadmap-Annahme falsch war (z.B. „Roadmap sagt 3 Trades, DB sagt 15 — alle 15 dokumentieren oder bei 3 bleiben mit Note?")
4. **Tiefe-Fragen klären** wenn ein Item destruktive Aktionen enthält (z.B. „A2 sagt 'Telegram-Send deaktivieren' — nur verifizieren, env-flag-guard, oder Code-Refactor?")

**Output dieser Phase**: User-bestätigte Reihenfolge + Scope + Tiefe für jedes Item.

### Phase 3 — Execution mit Discovery-Mandat

Pro Item:

1. **Reality-Check für dieses spezifische Item** (DB / docker / SSH / Filesystem)
2. **Wenn Item nicht mehr zutreffend ist** (z.B. „disable Services" — Services schon disabled):
   - NICHT pflichtschuldig „✓" schreiben
   - Stattdessen: Discovery dokumentieren („verifiziert: Services bereits disabled" + ggf. neuer Issue wenn Verify selbst was aufdeckt, z.B. „Backup fehlt")
3. **Wenn Item ein Vorgänger-Artefakt updated**: NICHT Edit-on-top, sondern Reality-Vergleich → falls drift > 30% → Komplett-Rewrite mit verifizierten Werten
4. **Wenn Item ein Code-Change ist**: dem üblichen TDD/Smoke-Test-Loop folgen (siehe `swatserver-fastapi-iteration` falls FastAPI, sonst project-spezifisch)
5. **Zwischen-Review** mit User vor dem nächsten Item

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| „Roadmap-Item A5 sagt 'X disable + Y confirm' → ich häkchen beides ab" | Verify-first: ist X schon disabled? Ist Y wirklich confirmed? Discovery-doc bei Diskrepanz |
| Vorgänger-Service-Map ergänzen ohne Reality-Check | Reality-Vergleich + Komplett-Rewrite wenn Drift > 30% |
| „Die Vorgänger-Session war 'done' mit dem Item, ich muss da nichts machen" | Vorgänger-`done`-Markierungen sind keine Verifikation; selbst messen |
| Discovery-Issues in einem File vergraben | Multi-File-Anker (analog `vault-decision-cross-file-sync`) — Hardware-Inventar + Service-Map + Repo-CLAUDE.md |
| Backup-Bestätigung als Pflicht-Häkchen ohne Test | Konkretes Test-Snippet: `ls /srv/backups-staging/` + `restic snapshots --json` + Container-Filter-Logik prüfen |

## Quick-Reference Reality-Check-Commands (Wolf-Stack)

```bash
# Container-Status auf swatserver
ssh eddie@100.121.72.86 "docker ps --filter name=<stack>"

# DB-Inhalt (User+DB-Name aus container env ableiten!)
ssh eddie@100.121.72.86 "docker inspect <db-container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES"
ssh eddie@100.121.72.86 "docker exec <db-container> psql -U <user> -d <db> -c '\dt'"

# Host-Timer + systemd-Status
ssh eddie@100.121.72.86 "systemctl list-timers --all | grep -v restic-system"

# Pi-Sanity (decommission-Check)
ssh eddie@botserver "crontab -l | grep -v '^#' ; systemctl --user list-unit-files --state=enabled"

# Backup-Coverage (Restic + Pre-Hooks)
ssh eddie@100.121.72.86 "cat /srv/projects/ops/restic-backup.sh ; ls -la /srv/backups-staging/"
```

## Real-world impact (25.05.2026)

Phase-A-Konsolidierungs-Session der `ultimative-platform` (6 Items A1-A6):

- **A1 Service-Map**: Vorgänger-Datei (datiert „2026-05-26" — Tippo) sagte „DB-User `postgres`, DB-Name `ultimative`, 11 Hypertables, Port 5433 extern". Reality: `eddie`/`trader`/7 Hypertables/kein Host-Port-Mapping. Edit-on-top wäre falsch geblieben — Komplett-Rewrite mit verifizierten Werten war richtig.

- **A4 v3-trades-open**: Vorgänger-Datei sagte „3 offene Trades #1, #3, #4" mit Entry-Preisen die um 30% von DB abwichen. Reality: 15 offene Trades (IDs 1, 3-16). User-Scope-Frage geklärt → alle 15 dokumentiert mit korrekten Entry/Stop/Hebel-Werten.

- **A5 Pi-Decommission**: Roadmap sagte „Services disablen, Backup confirmen". Reality: Services waren schon disabled — aber Backup war NICHT confirmed. `pre-backup-hooks/postgres-dumpall.sh` matcht den Container-Namen nicht, restic excludet `/srv/docker/**`, `/srv/backups-staging/` ist leer. Ohne Verify-First-Disziplin wäre „Backup confirmed ✓" der gefährlichste False-Positive der Session geworden.

- **A6 Repo-CLAUDE.md**: Pi-zentrische Datei updaten ohne Reality-Vergleich hätte das Pi-Stack-Inventar in der „Produktionsumgebung"-Tabelle behalten. Reality-First: Tabelle komplett auf swatserver-m720q umgestellt, alte Pi-Befehle als „HISTORISCH für Backup-Recovery" markiert.

**Ergebnis**: 30 % der Session-Zeit ging in Drift-Reparatur, 70 % in echte Umsetzung — und ein latent gefährliches Backup-Issue wurde aufgedeckt, das ohne Verify-First-Pattern liegen geblieben wäre.

## Cross-References

- `superpowers:writing-skills` — Iron-Law-Protokoll (warum dieser Skill als STUB markiert ist)
- `vault-decision-cross-file-sync` (auch Stub) — wie die Discovery-Issues multi-file verankert werden
- `brain-dump-to-phased-roadmap` — Vorstufe (Roadmap-Design), die diesen Skill mit Material versorgt
- Wolf-Maxime „Current Truth vor Timeline" (17.05.2026) in `.remember/core-memories.md` — das Mindset-Fundament
- Wolf-Maxime „In Konstruktionen messen, niemals schätzen" (03.05.2026) — die Engineering-Wurzel des Patterns

## TODO bevor STUB-Marker entfernt wird

1. **RED-Phase**: Subagent mit Pressure-Scenario „Phase Y implementieren, Vorgänger-Files vorhanden mit gemischter Drift" laufen lassen ohne diesen Skill. Dokumentieren welche Drift-Items gehäkchelt werden statt zu verify-discovern.
2. **GREEN-Phase**: Skill aktivieren, Pressure-Scenario wiederholen, verify dass Subagent jetzt verify-first macht.
3. **REFACTOR-Phase**: 2-3 Pressure-Iterations (Zeitdruck, „der Vorgänger hat doch alles vorbereitet, ich kann doch direkt drauf bauen", „Wolf will Tempo, ich überspringe die Verify-Schritte").
4. **Loopholes plugged**: Rationalization-Tabelle bauen, Red-Flags-Liste erstellen.
5. **`-STUB`-Suffix vom `name`-Feld entfernen** → auto-discoverable.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS — mit überraschendem GREEN-Verhalten)

- **RED-Subagent** (ohne Skill, Phase-A-Ausführen-Task): Vernünftige Antwort (b) Reality-Check first. Zitierte CLAUDE.md-Maximen direkt („Erst Logs/Code/DB lesen", „closed-as-done vermeiden"). Schlug konkrete Reality-Check-Reihenfolge vor (Daily Notes scannen, Git-Log, Live-Trades, Pi-Status, Service-Map-Vergleich). Sehr nahe am GREEN-Verhalten — RED ist hier auch klug.
- **GREEN-Subagent** (mit Skill, gleicher Prompt): Ging über RED hinaus — **las die existierende Roadmap-Datei im Vault** und entdeckte: Phase A ist bereits als ✅ DONE 2026-05-25 markiert mit vollständigem Audit-Log (Commits 7652561, f3fb7e9, b84fd07f-Snapshot). Drift-Tabelle gegen die Wolf-Anweisung erstellt. 3-Szenarien-Sanity-Frage gestellt (Test? Häkchen-Nachzug? Rückrollung?). **Kein Häkchen gesetzt, keine Datei editiert** — Phase 3 (Execution) gegated bis Wolf antwortet.
- **Verdict**: GREEN klar überlegen — vermied False-Positive-„Häkchen-für-Häkchen"-Ausführung obwohl Phase bereits done war. RED wäre vermutlich in Phase 1 (Reality-Check) hängengeblieben ohne die Roadmap selbst zu öffnen.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Fallback-Mode für No-SSH-Tool-Subagent** dokumentieren (Vault-as-Reality-Proxy + Audit-Log-Cross-Reference + explicit Command-Listing) — wie der GREEN-Subagent es heute substituiert hat
2. **Anti-Pattern-Zeile** ergänzen: „Phase bereits done → Skill-Output ist Drift-Report, NICHT Häkchen-Nachzug ohne Reality-Check"
3. **Trust-Boundary-Check-Sektion**: was tun bei Widerspruch zwischen Wolf-Anweisung und Vault-Audit-Log? Sanity-Frage VOR Edit, kein Auto-Resolve.
4. **Skill-Composition-Hinweis**: braucht `communication-preferences` (Sanity-Frage-Tonalität) + `vault-decision-cross-file-sync` (Multi-File-Discovery-Verankerung)
