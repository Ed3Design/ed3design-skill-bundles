---
name: forensik-spur-fuer-fire-and-forget-sends
description: Use when designing or hardening any "send + log + swallow" pattern (Telegram bot sends, email notifications, webhook dispatches, Slack pings, push notifications, SMS sends, alert dispatcher) where (a) DB-state persistence is separated from external API send, (b) send errors are silently fail-open via log-only, and (c) future forensics may need to distinguish "send happened, user missed" from "send never happened" without relying on log-aggregator availability. Trigger on phrases like "log.warning on send-fail", "fire-and-forget Telegram", "why didn't the notification arrive", "send discrepancy", "DB save ran but Telegram didn't", "container logs are gone", "forensics without logs", "send + swallow pattern", "*_sent_at column", "asyncio.create_task send", "advisor send forensics". Skill produces (1) one-time DB migration for `*_sent_at TIMESTAMPTZ`, (2) update-after-send-OK persistence, (3) forensic query template for discrepancy detection. Do NOT load for synchronous send-and-wait patterns where the send result is the immediate caller return value (then check the return value, no DB trail needed), for sends where container logs are guaranteed persistent (e.g. external log aggregator like Datadog/Sentry for ALL services — then logs are sufficient), or for one-off ad-hoc scripts (overkill for 30-min scripts). Encodes a real-world trap: a per-signal advisor's DB save ran successfully (2 assessments), Telegram send fail-open log.warning, container restart erased logs before that point → no forensics possible. With a `telegram_sent_at` column: a SQL query immediately shows which sends failed, log-independent.
---

# Forensic trail for fire-and-forget sends

## Overview

The pattern "DB save → external send → log.warning on send-fail" is nice for resilience, but on container restart or log rotation the send-fail forensics are gone. When the user asks the next morning "why didn't my notification arrive?", you have to say "I don't know, logs are toast".

**Core principle:** every external-send action needs a DB trail (`*_sent_at`) as a log-independent audit layer.

## When to use

- Telegram bot sends (action trigger or notification)
- Email dispatch (transactional or marketing)
- Webhook POSTs to external services
- Slack/Discord channel pings
- SMS sends via Twilio / etc.
- Push notifications (FCM/APN)
- Alert dispatcher (any external integration)
- Async `asyncio.create_task(send_x())` (mitigates the silent-error class)

## When NOT to use

- Sync send-and-wait where the caller has the send result directly
- External log aggregator (Datadog/Sentry/etc.) persistently covers ALL services
- Ad-hoc scripts with short lifetime
- Sends with their own external receipt tracking (e.g. Twilio status callback into your own DB)

## The 4-step procedure

### Step 1 — DB migration: `*_sent_at TIMESTAMPTZ`

```sql
ALTER TABLE <state_table>
ADD COLUMN IF NOT EXISTS <channel>_sent_at TIMESTAMPTZ;
```

Idempotent + additive. Conventions:
- `telegram_sent_at` for Telegram sends
- `email_sent_at` for mails
- `webhook_posted_at` for webhooks
- `slack_sent_at` etc.

For multiple channels: separate columns. For ONE send per row: dedicated column directly. For 1:n (multiple sends per row over time): a separate `*_dispatches` table.

### Step 2 — Update logic after send-OK

```python
async def _send_x(record_id: int, ..., conn=None):
    try:
        await external_api.send(...)
    except Exception as exc:
        log.error("Send-Fail (record_id=%s): %s", record_id, exc)
        return False

    # Forensic trail
    if conn is not None:
        try:
            await conn.execute(
                "UPDATE <state_table> SET <channel>_sent_at = NOW() "
                "WHERE id = $1",
                record_id,
            )
        except Exception as exc:
            log.warning("sent_at update failed: %s", exc)

    return True
```

**Important**: update INSIDE the send function, NOT from the caller. Otherwise the caller can forget and the trail is gone again.

### Step 3 — Forensic query as a template snippet

In a code comment or a dedicated `docs/forensics/send-discrepancy.md`:

```sql
-- Which records had DB save but no successful send (= send-fail)?
SELECT id, <key-columns>, created_at
FROM <state_table>
WHERE <channel>_sent_at IS NULL
  AND created_at < NOW() - INTERVAL '1 minute'  -- send-completion margin
ORDER BY created_at DESC
LIMIT 50;
```

Margin: large enough for send latency, small enough not to show current in-flight sends.

### Step 4 — Tests + docs

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

- ❌ **Update before send** — `UPDATE sent_at` BEFORE the actual send → mark as sent when actually failed
- ❌ **Update from caller** — caller forgets update or race condition
- ❌ **Status column instead of timestamp** (`status='sent'`) — loses the "when" information for latency forensics
- ❌ **Index on `*_sent_at IS NULL`** without partial index — can become expensive on large tables. Use `CREATE INDEX ... WHERE sent_at IS NULL` for the most common forensic query
- ❌ **Send + update in one transaction** — if send takes 30s, this holds the DB connection longer than needed. Separate transactions.

## Worked example

User-driven forensics: in the morning at 06:02 UTC, two advisor outputs were persisted in `claude_assessments` (id=140 SI=F, id=141 ZC=F), but no Telegram arrived. A container restart at 09:03 UTC erased the logs — the send-fail cause was unprovable.

**Fix**:
```sql
ALTER TABLE claude_assessments
ADD COLUMN IF NOT EXISTS telegram_sent_at TIMESTAMPTZ;
```

Plus update-after-send-OK in `_send_advisor_telegram`.

**Cycle-2 forensic query** (in code comment):
```sql
SELECT id, symbol, direction, created_at FROM claude_assessments
WHERE telegram_sent_at IS NULL
  AND model='per_signal_advisor'
  AND created_at < NOW() - INTERVAL '1 minute';
```

That way, every future send discrepancy is readable from the DB in <1s, log-independent.

## Skill-Composition

- `superpowers:test-driven-development` — for the send tests
- `library-subclass-explicit-type-classification-DRAFT` — when send errors need to be classified as retry/fail-fast (see the twin skill)
- The project CLAUDE.md your-app section — document the pattern there as a backlog hint

## Why this is overlooked (common cause of regret)

During implementation, one believes "log.warning is robust enough — logs are persistent". But:
- **Container restart** (deploy, OOM kill, health-check failure) → in-memory logs gone
- **Log rotation** (logrotate, k8s fluentd quotas) → older logs gone
- **Log-aggregator outage** → nothing gets forwarded anymore
- **Production stress spike** → log buffer overruns

Precisely in those cases you need forensics MORE than usual. The DB trail is 1× migration + 5 lines of code, against years of future sessions of forensic value.
