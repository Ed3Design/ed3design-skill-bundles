---
name: async-context-manager-retry-pattern
description: |-
  Use when implementing retry-logic around an `async with X:` block where `X.__aenter__()` or `X.__aexit__()` itself performs network-IO that can fail transiently — for example python-telegram-bot's `async with Bot(token) as bot:` (calls `initialize()` with HTTPX-connection-setup that can TimedOut), asyncpg's `async with pool.acquire() as conn:` (TCP-handshake can fail), httpx `async with AsyncClient() as c:` (TLS-handshake), or websockets `async with connect(url) as ws:` (WS-upgrade-handshake). The Iron-Law: every `async with` whose enter/exit does network-IO must sit INSIDE the retry-loop, not around it — otherwise enter-failures fly past the inner `try/except` and get caught by an outer `except Exception` as "Unexpected", with zero retries actually attempted. Trigger on phrases like "retry around async with", "TimedOut from __aenter__", "connection-setup in retry-loop", "unexpected send-error despite retry-logic", "retry never fires", "I implemented retry but it doesn't trigger", "fresh connection per attempt", "async context manager retry pitfall", "context manager exception bypasses retry", "how to wrap async with in retries". Do NOT load for SYNC context-managers (different exception-propagation model, less common pitfall — sync `with X:` rarely does heavy IO), for async-with where __aenter__ does only-local-work like file-open or in-memory state (no network → no transient retries needed), for retry around a generator-based async-iterator (different pattern entirely — `async for` retry has its own consideration), or for first-time-design of an async-context-manager class itself (use "building async-context-managers" guidance instead — that's the producer side, this skill is consumer side).

---

# Async-Context-Manager Retry Pattern

## The Iron Law

> If your retry-loop wraps `async with X:` instead of being wrapped BY it, your retry-logic is fictional for the most common transient-failure mode: connection-setup-timeout.

## The trap (concrete example)

### Wrong (originally deployed)

```python
try:
    async with bot:                  # ← __aenter__ TimedOut flies past
        for attempt in range(MAX_RETRIES + 1):
            try:
                await bot.send_message(...)
                break
            except TelegramError as exc:
                if not is_retryable(exc):
                    return False
                # retry logic lives HERE
                await asyncio.sleep(delays[attempt])
except Exception as exc:             # ← catches __aenter__ TimedOut
    log.error("Unexpected send-error: %s", exc)
    return False                     # ← Zero retries done!
```

**Bug effect**: `Bot.__aenter__()` calls `initialize()` with HTTPX connection-setup. When that raises TimedOut, the exception flies OUTSIDE the inner retry `try`, gets caught by the outer `except Exception`, and **the retry loop is never entered** — even though retry logic is present.

**Live evidence**: 6 seconds between DB-Save and Error-Log. A real 3-retry pass with backoff [1s, 2s, 4s] + 4 × ~5s default-timeout = ~27 seconds. The gap proves no retry ran.

### Right

```python
last_exc = None
for attempt in range(MAX_RETRIES + 1):
    bot = create_bot(token)              # ← Fresh Bot instance per attempt
    try:
        async with bot:                  # ← __aenter__ NOW inside retry scope
            await bot.send_message(...)
        last_exc = None
        break  # success
    except TelegramError as exc:
        if not is_retryable(exc):
            log.error("fail-fast: %s", type(exc).__name__)
            return False
        last_exc = exc
        if attempt >= MAX_RETRIES:
            break
        delay = delays[attempt]
        if isinstance(exc, RetryAfter):
            delay = max(delay, exc.retry_after)
        await asyncio.sleep(delay)
    except Exception as exc:
        log.error("Unexpected send-error: %s", exc)
        return False

return last_exc is None
```

Note:
1. `async with bot:` is INSIDE the `for attempt in range(...)` loop
2. Bot instance is freshly created in EACH iteration — fresh connection pool
3. The `try/except TelegramError` now wraps both `__aenter__` and `bot.send_message()` — both failure modes get retry-classified

## Why this matters generally

Each of the following patterns has the same failure path:

| Library | Risky `__aenter__` does |
|---|---|
| python-telegram-bot `async with Bot(...) as bot` | HTTPX-Client-Init, possibly `initialize()` with getMe() |
| httpx `async with AsyncClient(...) as c` | Transport-Setup, may stall on SSL handshakes |
| asyncpg `async with pool.acquire() as conn` | TCP-handshake to Postgres, TLS-upgrade, Auth-roundtrip |
| websockets `async with connect(url) as ws` | TCP + WS upgrade handshake |
| aiohttp `async with session.get(url) as resp` | Connection + Request + Initial-Response-Header |
| aiokafka `async with consumer:` | Broker connection + Group coordination |

All have non-trivial IO in `__aenter__`. If your retry loop sits around them, you have not covered them.

## Test discipline (the real lesson)

**Test gap**: all 3 retry-tests mocked `FakeBotClass.__aenter__` as a trivial stub:
```python
class FakeBotClass:
    async def __aenter__(self): return self   # ← never fails
    async def __aexit__(self, *a): return None
    async def send_message(self, **k): ...    # ← test only mocks THIS
```

That made the test green, but the real failure mode (`__aenter__` raises TimedOut) was completely uncovered.

**Fix-Test pattern**: at least ONE test per library where `__aenter__` itself raises a retryable exception:

```python
class FakeBotClass:
    aenter_calls = {"n": 0}
    async def __aenter__(self):
        FakeBotClass.aenter_calls["n"] += 1
        if FakeBotClass.aenter_calls["n"] < 3:
            raise TimedOut("connection-setup-timeout")
        return self
    async def __aexit__(self, *a): return None
    async def send_message(self, **k): return None  # never fails
```

Expectation:
- `aenter_calls["n"] == 3` (2 failures + 1 success)
- `send_calls["n"] == 1` (send_message is reached only once — on the successful attempt)
- `sleeps == [1.0, 2.0]` (2 backoffs between the 3 attempts)

## The 4-Step Refactor Procedure

### Step 1 — Audit: what does `__aenter__` actually do?

Read library docs or source code:
- python-telegram-bot 22.x: `Bot.__aenter__` → `initialize()` → `httpx.AsyncClient` setup + optional `getMe()` call
- asyncpg: `pool.acquire().__aenter__` → connect + TLS + auth
- httpx: `AsyncClient.__aenter__` → usually just in-memory state but `aclose` drains the connection pool

If `__aenter__` does network IO: include it in the retry scope.

### Step 2 — Refactor: Context-Manager INTO the loop

Before:
```python
async with X:
    for attempt in retries: try send except retry sleep
```

After:
```python
for attempt in retries:
    X = create_fresh()        # ← optional: fresh resource per attempt
    try:
        async with X:
            await operation()
        break
    except RetryableErr: sleep
    except NonRetryableErr: return
```

### Step 3 — RED test with `__aenter__` failure

Write a test where `__aenter__` fails multiple times. **It must be red before the fix** — otherwise you didn't have the bug pattern.

### Step 4 — GREEN: apply refactor, test green

Plus: existing "send-fails-but-aenter-ok" tests must remain green (regression).

## Anti-patterns

- ❌ **"My retry loop is INSIDE the async with"** — you only retry the operation call, not the setup. Connection-Setup-TimedOut flies through.
- ❌ **Singleton resource in the retry loop** — if you use ONE Bot instance and the connection state is corrupt, you retry against the same broken state. Solution: `create_fresh()` per iteration.
- ❌ **`except Exception` outside the retry loop** — catches too much, masks Connection-Setup-Failures as "Unexpected". If at all: log BEFORE the loop + raise.
- ❌ **Test mocks `__aenter__` as a trivial stub** — you are then not testing the hot path. At least one test with `__aenter__` failure.
- ❌ **Retry counter in a class attribute instead of a closure** — across multiple test cases in the same process, counters from the previous test stick around. Fresh instance per test.

## Skill-Composition

- `superpowers:test-driven-development` — runs AROUND this skill (RED-Test with __aenter__-failure → GREEN-Refactor)
- `library-subclass-explicit-type-classification-DRAFT` — complementary aspect: WHICH exceptions are retryable? This skill: WHERE does retry take effect?
- `forensik-spur-fuer-fire-and-forget-sends-DRAFT` — orthogonal: DB-trail on Send-Fail so silent failure does not stay silent
- `asyncpg-live-vs-mock-shape` — different aspect of mock-vs-live divergence (Type-Coercion, not Context-Manager-Setup)

## When-Built / Why-Built

Built after a forensic investigation:

- ~12:00 user feedback that the morning signal had no advisory
- ~12:30 deployed initial retry logic (all 3 tests green)
- ~14:02 next signal: DB-Save OK, Telegram-Send TimedOut → "Unexpected send-error", **no retry**
- ~16:30 user feedback: "still no advisory despite the fix"
- ~16:45 forensics in journalctl, root cause clear
- ~17:00 RED-Test with __aenter__-TimedOut → exactly the production log string
- ~17:10 GREEN-Refactor: `async with bot` moved into the loop, fresh Bot per attempt
- ~17:25 Live-Verify with a re-send for assessment #145 → 200 OK, telegram_sent_at set

Bug-Lifetime: ~9 hours between Deploy and Discovery, despite green tests. **Test-pattern gap** (trivial __aenter__ mocks) was the structural cause.

Promotion-Trigger: ≥2 further live applications outside python-telegram-bot (e.g. asyncpg-pool-acquire retry, httpx-client-setup retry).
