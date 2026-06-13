---
name: forensik-spur-fuer-fire-and-forget-sends
description: Use when designing or hardening any "send + log + swallow"-Pattern (Telegram-Bot-Sends, Email-Notifications, Webhook-Dispatches, Slack-Pings, Push-Notifications, SMS-Sends, alert-dispatcher) where (a) DB-State persistence is separated from external-API-Send, (b) Send-Errors are silently fail-open via log-only, and (c) future forensics may need to distinguish "send happened, user missed" from "send never happened" without relying on log-aggregator availability. Trigger on phrases like "log.warning bei Send-Fail", "fire-and-forget Telegram", "warum kam die Nachricht nicht", "Send-Discrepancy", "DB-Save lief aber Telegram nicht", "Container-Logs sind weg", "Forensik ohne Logs", "send + swallow Pattern", "*_sent_at column", "asyncio.create_task send", "advisor send forensik". Skill produces (1) one-time DB-migration für `*_sent_at TIMESTAMPTZ`, (2) Update-nach-Send-OK Persistenz, (3) Forensik-Query-Template für Discrepancy-Detection. Do NOT load for synchronous send-and-wait patterns where the Send-Result is the immediate caller-return-value (then check the return-value, no DB-Spur needed), for sends where Container-Logs are guaranteed-persistent (e.g. external log-aggregator like Datadog/Sentry für ALL services — then logs are sufficient), or for one-off ad-hoc scripts (overkill für 30-min-Skripts). Encodes the 03.06.2026 ultimative-platform E-7.3 trap: per_signal_advisor DB-Save lief erfolgreich (2 assessments), Telegram-Send fail-open log.warning, Container-Restart 09:03 UTC hat Logs vor diesem Zeitpunkt gelöscht → keine Forensik mehr möglich. Mit `telegram_sent_at`-Spalte: SQL-Query zeigt sofort welche Sends fehlschlugen, log-unabhängig.
---

# Forensik-Spur für Fire-and-Forget-Sends

## Overview

Pattern "DB-Save → External-Send → log.warning bei Send-Fail" ist nice für resilience, aber bei Container-Restart oder Log-Rotation ist die Send-Fail-Forensik weg. Wenn der User morgens fragt "warum kam meine Notification nicht?", musst du sagen "weiß nicht, Logs sind futsch".

**Core principle:** Jede External-Send-Action braucht eine DB-Spur (`*_sent_at`) als log-unabhängiger Audit-Layer.

## When to use

- Telegram-Bot-Sends (action-trigger oder notification)
- Email-Dispatch (transactional oder marketing)
- Webhook-Posts an externe Services
- Slack/Discord-Channel-Pings
- SMS-Sends via Twilio / etc.
- Push-Notifications (FCM/APN)
- Alert-Dispatcher (any external integration)
- Async `asyncio.create_task(send_x())` (gemildert silent-error-Klasse)

## When NOT to use

- Sync send-and-wait wo Caller den Send-Result direkt hat
- External log-aggregator (Datadog/Sentry/etc.) deckt persistent ALL services
- Ad-hoc scripts mit kurzer Lebensdauer
- Sends mit eigener External-Receipt-Tracking (z.B. Twilio Status-Callback in eigene DB)

## The 4-step procedure

### Step 1 — DB-Migration: `*_sent_at TIMESTAMPTZ`

```sql
ALTER TABLE <state_table>
ADD COLUMN IF NOT EXISTS <channel>_sent_at TIMESTAMPTZ;
```

Idempotent + additiv. Conventions:
- `telegram_sent_at` für Telegram-Sends
- `email_sent_at` für Mails
- `webhook_posted_at` für Webhooks
- `slack_sent_at` etc.

Wenn mehrere Channels: separate Spalten. Wenn EIN-Send-pro-Row: dedicated Spalte direkt. Wenn 1:n (mehrere Sends pro Row über Zeit): separate `*_dispatches`-Tabelle.

### Step 2 — Update-Logik nach Send-OK

```python
async def _send_x(record_id: int, ..., conn=None):
    try:
        await external_api.send(...)
    except Exception as exc:
        log.error("Send-Fail (record_id=%s): %s", record_id, exc)
        return False

    # Forensik-Spur
    if conn is not None:
        try:
            await conn.execute(
                "UPDATE <state_table> SET <channel>_sent_at = NOW() "
                "WHERE id = $1",
                record_id,
            )
        except Exception as exc:
            log.warning("sent_at-Update fehlgeschlagen: %s", exc)

    return True
```

**Wichtig**: Update INNERHALB des Send-Funktion, NICHT vom Caller. Sonst kann Caller vergessen und Spur ist wieder weg.

### Step 3 — Forensik-Query als Template-Snippet

Im Code-Comment oder einer dedicated `docs/forensics/send-discrepancy.md`:

```sql
-- Welche Records hatten DB-Save aber kein erfolgreichen Send (= Send-Fail)?
SELECT id, <key-columns>, created_at
FROM <state_table>
WHERE <channel>_sent_at IS NULL
  AND created_at < NOW() - INTERVAL '1 minute'  -- send-completion margin
ORDER BY created_at DESC
LIMIT 50;
```

Margin: groß genug für Send-Latency, klein genug um aktuelle in-flight sends nicht zu zeigen.

### Step 4 — Tests + Doc

```python
async def test_sent_at_set_on_send_ok():
    # mock external send → success
    # call _send_x with conn + record_id
    # assert SELECT sent_at FROM table WHERE id=record_id IS NOT NULL

async def test_sent_at_null_on_send_fail():
    # mock external send → raise
    # call _send_x with conn + record_id
    # assert returns False, sent_at IS NULL
```

## Anti-patterns

- ❌ **Update vor Send** — `UPDATE sent_at` BEFORE the actual send → mark as sent when actually failed
- ❌ **Update aus Caller** — Caller vergisst Update oder Race-Condition
- ❌ **Status-Spalte statt Timestamp** (`status='sent'`) — verliert die "wann"-Information für Latenz-Forensik
- ❌ **Index auf `*_sent_at IS NULL`** ohne partial-index — kann teuer werden bei großen Tabellen. Use `CREATE INDEX ... WHERE sent_at IS NULL` für die häufigste Forensik-Query
- ❌ **Send + Update in einer Transaction** — wenn Send 30s dauert, hält das die DB-Connection länger als nötig. Separate Transactions.

## Worked example (03.06.2026 — E-7.3)

Wolf-Forensik: heute morgen 06:02 UTC zwei Advisor-Outputs in `claude_assessments` persistiert (id=140 SI=F, id=141 ZC=F), aber kein Telegram angekommen. Container-Restart 09:03 UTC hat Logs gelöscht — Send-Fail-Ursache nicht beweisbar.

**Fix**: 
```sql
ALTER TABLE claude_assessments
ADD COLUMN IF NOT EXISTS telegram_sent_at TIMESTAMPTZ;
```

Plus update-nach-Send-OK in `_send_advisor_telegram`.

**Cycle-2-Forensik-Query** (in Code-Comment):
```sql
SELECT id, symbol, direction, created_at FROM claude_assessments
WHERE telegram_sent_at IS NULL
  AND model='per_signal_advisor'
  AND created_at < NOW() - INTERVAL '1 minute';
```

Damit ist jede Future-Send-Discrepancy in <1s aus DB ablesbar, log-unabhängig.

## Skill-Composition

- `superpowers:test-driven-development` — für die Send-Tests
- `library-subclass-explicit-type-classification-DRAFT` — wenn Send-Errors nach Retry/Fail-Fast klassifiziert werden müssen (siehe E-7.3.2 als Twin-Skill)
- Wolf-Vault CLAUDE.md ultimative-platform-Sektion — Pattern dort als Backlog-Hint dokumentieren

## Why this is overlooked (common cause of regret)

Bei Implementation glaubt man "log.warning ist robust genug — Logs sind ja persistent". Aber:
- **Container-Restart** (Deploy, OOM-Kill, Health-Check-Failure) → in-memory Logs weg
- **Log-Rotation** (logrotate, k8s-fluentd-quotas) → ältere Logs weg
- **Log-Aggregator-Outage** → nichts wird mehr durchgereicht
- **Production-Stress-Spike** → Log-Buffer overruns

Genau in diesen Fällen brauchst du die Forensik MEHR als sonst. DB-Spur ist 1× Migration + 5 Zeilen Code, gegen jahrelang Future-Sessions Forensik.
