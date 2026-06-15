---
name: db-telemetry-primary-docker-logs-secondary
description: |-
  Use when investigating missing or unexplained behavior in a containerized stack where a high-volume job (MQTT ingester, 5m-fetcher, scraper) runs in the same container as diagnostic jobs, and Docker logs show nothing for the time period in question. Symptom: `docker logs --since 72h` returns only recent lines; older diagnostic entries are gone despite the container running continuously. Root cause: Docker's default JSON log driver rotates files at ~10MB — high-volume sibling output pushes out older diagnostic lines within hours. Fix: query DB-side telemetry (tick_log, job_log, metrics tables) as primary source; Docker logs are only reliable for the last 30–60 minutes. Trigger on phrases like "docker logs shows nothing", "no logs from yesterday", "log rotation", "scheduler history gone", "where are Friday's logs". Do NOT load for fresh containers without DB telemetry infrastructure, single-process containers where log rotation isn't an issue, or log-streaming setups (Loki, CloudWatch, Datadog).

---

# db-telemetry-primary-docker-logs-secondary

> ✅ **PROMOTED**: RED subagent arrived at the same log-rotation hypothesis (H1) but started with Docker-diagnosis attempts. GREEN subagent: DB telemetry (`tick_log`) first, found the log-rotation confirmation + two bonus findings (quarantine logic, missing TOUCH pattern) that Docker logs would never have shown.

## Core Problem

In containerized stacks with mixed job frequencies, a high-volume process destroys diagnostic history:

- **5m-fetcher** → 600k log lines / 72h → rotates the Docker log buffer in hours
- **v3_live_monitor** (every 15 min) → ~288 entries / 72h → displaced by rotation
- **Result**: `docker logs --since 72h | grep "live_monitor"` → 4 entries instead of 288

**Root cause example**: a 2.5d watcher gap could not be reconstructed because the relevant logs had rotated for 3 days. The diagnostic source was `tick_log` in the DB (full history since container start).

## Diagnosis Order

### Step 1 — DB telemetry first

```sql
-- Job history: all runs of a service with error detail
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

JSONB meta often contains per-run details (`errors[]`, counters, symbols). **Verify schema before query**: `\d tick_log` — columns can vary by project (`ts_started` vs `created_at`, `service_name` vs `job_name`).

### Step 2 — Docker logs only for current events

```bash
# Safe: only the last 30 minutes
docker logs <container> --since 30m

# Unsafe with high-volume siblings: "since 72h" can be empty
docker logs <container> --since 72h  # ← may be empty even though container ran 3 days
```

### Step 3 — Detect log rotation

```bash
# Shows whether logs really start today:
docker logs <container> --since 72h 2>&1 | head -1
# If the first entry is < 2h old → rotation has displaced older entries

# Check log config:
docker inspect <container> --format '{{json .HostConfig.LogConfig}}'
# {"Type":"json-file","Config":{"max-file":"1","max-size":"10m"}} → rotation confirmed
```

## Preventive: build DB telemetry

For every scheduled job:
1. `tick_log` INSERT at start with `ts_started`
2. `tick_log` UPDATE at end with `exit_status`, `error_message`, `meta JSONB`
3. Counters in `meta`: `n_processed`, `n_skipped`, `n_errors`, `errors: []`

Pattern from your-app `_tick_log_start()` / `_tick_log_finish()`.

## When Docker logs are reliable

- Last ~30 minutes (before rotation)
- Low-volume containers without high-frequency siblings
- Containers with a configured external log driver (Loki, Fluentd, CloudWatch)
- `docker run --log-opt max-size=100m --log-opt max-file=10` (explicitly larger buffer)

## Background: TDD Log (Bulletproofing)

### Cycle 1 — PASS

- **RED subagent** (without skill): arrived at the log-rotation hypothesis, but after several alternative hypotheses (code silence, container restart, timezone). Proposed DB query `last_zone_check_at` as the "decisive test" — but only after 3 docker-diagnosis attempts. The ORDER was wrong (Docker-first, DB-second).
- **GREEN subagent** (with skill): Step 1 (DB telemetry) executed immediately. Found log-rotation confirmation (609k lines, 10MB buffer). Bonus: discovered quarantine logic (CL=F no longer checked) + missing TOUCH pattern (BAS.DE never updated despite successful scans). Both findings would have been undiscoverable with Docker-logs only.
- **Refactor**: schema-verify hint for `tick_log` added (columns vary by project), log-config-inspect command added.

### Cycle-2 Backlog (non-blocking)

1. No-TOUCH pattern: if DB telemetry shows success but trade-updates are missing → check whether the monitor only updates on `stage_change` (not on every scan). Sub-skill candidate.
2. Tick-Gap detection: helper query that computes the maximum gap between runs (expected: ≤15min for v3_live_monitor).
