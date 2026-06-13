---
name: db-telemetry-primary-docker-logs-secondary
description: Use when investigating missing or unexplained behavior in a containerized stack where a high-volume job (MQTT ingester, 5m-fetcher, scraper) runs in the same container as diagnostic jobs, and Docker logs show nothing for the time period in question. Symptom: `docker logs --since 72h` returns only recent lines; older diagnostic entries are gone despite the container running continuously. Root cause: Docker's default JSON log driver rotates files at ~10MB — a high-volume sibling process pushes out older, low-frequency diagnostic log lines within hours. Fix pattern: query DB-side telemetry (tick_log, job_log, metrics tables) as the primary source; Docker logs are only reliable for the last 30–60 minutes. Trigger on phrases like "docker logs zeigt nichts", "keine Logs von gestern", "Log-Rotation", "kann nicht finden was der Job gemacht hat", "Scheduler-History weg", "ich sehe nur heutige Logs", "wo sind die Logs von Freitag". Do NOT load for fresh containers without DB telemetry infrastructure, for single-process containers where log rotation isn't an issue, or for log-streaming setups (Loki, CloudWatch, Datadog) that aggregate externally.
---

# db-telemetry-primary-docker-logs-secondary

> ✅ **PROMOTED 2026-06-08**: RED-Subagent kam zur gleichen Log-Rotation-Hypothese (H1), startete aber mit Docker-Diagnosis-Versuchen. GREEN-Subagent: DB-Telemetrie (`tick_log`) zuerst, fand die Log-Rotation-Bestätigung + zwei Bonus-Befunde (Quarantäne-Logik, fehlendes TOUCH-Pattern) die Docker-Logs nie gezeigt hätten.

## Core Problem

In containerized stacks with mixed job frequencies, a high-volume process destroys diagnostic history:

- **5m-Fetcher** → 600k log lines / 72h → rotiert Docker-Log-Buffer in Stunden
- **v3_live_monitor** (alle 15 min) → ~288 Einträge / 72h → von Rotation verdrängt
- **Ergebnis**: `docker logs --since 72h | grep "live_monitor"` → 4 Einträge statt 288

**Root Cause gefunden 08.06.2026**: 2.5d Watcher-Gap konnte nicht rekonstruiert werden, weil relevante Logs seit 3 Tagen rotiert waren. Diagnose-Quelle war `tick_log` in der DB (vollständige History seit Container-Start).

## Diagnose-Reihenfolge

### Schritt 1 — DB-Telemetrie zuerst

```sql
-- Job-History: Alle Runs eines Services mit Fehler-Details
SELECT
  ts_started::timestamptz AT TIME ZONE 'UTC' as started,
  exit_status,
  n_symbols_scanned,
  error_message,
  meta
FROM tick_log
WHERE service_name = 'v3_live_monitor'
  AND ts_started >= NOW() - INTERVAL '72 hours'
ORDER BY ts_started DESC
LIMIT 50;
```

JSONB-Meta enthält oft per-run Details (`errors[]`, Zähler, Symbole). **Schema vor Query verifizieren**: `\d tick_log` — Spalten können projektspezifisch abweichen (`ts_started` vs `created_at`, `service_name` vs `job_name`).

### Schritt 2 — Docker-Logs nur für aktuelle Events

```bash
# Sicher: nur die letzten 30 Minuten
docker logs <container> --since 30m

# Unsicher bei High-Volume-Siblings: "since 72h" kann leer sein
docker logs <container> --since 72h  # ← kann leer sein obwohl Container 3 Tage läuft
```

### Schritt 3 — Log-Rotation erkennen

```bash
# Zeigt ob logs wirklich nur heute beginnen:
docker logs <container> --since 72h 2>&1 | head -1
# Wenn erster Eintrag < 2h alt → Rotation hat ältere Einträge verdrängt

# Log-Config prüfen:
docker inspect <container> --format '{{json .HostConfig.LogConfig}}'
# {"Type":"json-file","Config":{"max-file":"1","max-size":"10m"}} → Rotation bestätigt
```

## Präventiv: DB-Telemetrie aufbauen

Für jeden Scheduled-Job:
1. `tick_log` INSERT am Start mit `ts_started`
2. `tick_log` UPDATE am Ende mit `exit_status`, `error_message`, `meta JSONB`
3. Zähler in `meta`: `n_processed`, `n_skipped`, `n_errors`, `errors: []`

Pattern aus ultimative-platform `_tick_log_start()` / `_tick_log_finish()`.

## Wann Docker-Logs zuverlässig sind

- Letzte ~30 Minuten (vor Rotation)
- Low-volume Container ohne High-Frequency-Siblings
- Container mit konfiguriertem externem Log-Driver (Loki, Fluentd, CloudWatch)
- `docker run --log-opt max-size=100m --log-opt max-file=10` (explizit größerer Buffer)

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-08 (PASS)

- **RED-Subagent** (ohne Skill): Kam zur Log-Rotation-Hypothese, aber nach mehreren alternativen Hypothesen (Code-Silence, Container-Restart, Timezone). Schlug DB-Query `last_zone_check_at` als "entscheidenden Test" vor — aber erst nach 3 docker-Diagnose-Versuchen. Die ORDER war falsch (Docker-first, DB-second).
- **GREEN-Subagent** (mit Skill): Schritt 1 (DB-Telemetrie) sofort ausgeführt. Fand Log-Rotation-Bestätigung (609k Zeilen, 10MB-Buffer). Bonus: entdeckte Quarantäne-Logik (CL=F nicht mehr gecheckt) + fehlendes TOUCH-Pattern (BAS.DE nie upgedated trotz erfolgreicher Scans). Beide Befunde wären mit Docker-Logs-only nicht auffindbar gewesen.
- **Refactor**: Schema-Verify-Hinweis für `tick_log` hinzugefügt (Spalten projektspezifisch), Log-Config-Inspect-Befehl ergänzt.

### Cycle-2-Backlog (nicht-blocking)

1. No-TOUCH-Pattern: wenn DB-Telemetrie success zeigt aber Trade-Updates fehlen → prüfe ob Monitor nur bei `stage_change` updated (nicht bei jedem Scan). Eigenes Sub-Skill kandidat.
2. Tick-Gap-Detection: Helper-Query der die maximale Lücke zwischen Runs berechnet (erwartet: ≤15min für v3_live_monitor).
