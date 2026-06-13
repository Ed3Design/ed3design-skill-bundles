---
name: async-context-manager-retry-pattern
description: Use when implementing retry-logic around an `async with X:` block where `X.__aenter__()` or `X.__aexit__()` itself performs network-IO that can fail transiently — for example python-telegram-bot's `async with Bot(token) as bot:` (calls `initialize()` with HTTPX-connection-setup that can TimedOut), asyncpg's `async with pool.acquire() as conn:` (TCP-handshake can fail), httpx `async with AsyncClient() as c:` (TLS-handshake), or websockets `async with connect(url) as ws:` (WS-upgrade-handshake). The Iron-Law: every `async with` whose enter/exit does network-IO must sit INSIDE the retry-loop, not around it — otherwise enter-failures fly past the inner `try/except` and get caught by an outer `except Exception` as "Unexpected", with zero retries actually attempted. Trigger on phrases like "Retry um async with", "TimedOut aus __aenter__", "Connection-Setup im Retry-Loop", "Unexpected send-error trotz retry-logic", "Retry erschöpft sich nicht", "ich habe Retry implementiert aber er greift nicht", "fresh connection pro Versuch", "async context manager retry pitfall", "context manager exception bypasses retry", "wie wraps man async with mit retries". Do NOT load for SYNC context-managers (different exception-propagation model, less common pitfall — sync `with X:` rarely does heavy IO), for async-with where __aenter__ does only-local-work like file-open or in-memory state (no network → no transient retries needed), for retry around a generator-based async-iterator (different pattern entirely — `async for` retry has its own consideration), or for first-time-design of an async-context-manager class itself (use „building async-context-managers" guidance instead — that's the producer side, this skill is consumer side). Encodes the 03.06.2026 ultimative-platform E-7.3.3 trap: Bot-Connection-TimedOut from `async with bot:` flew past 3-retry-loop, was caught as "Unexpected send-error" with zero retries — 9 hours between fix-deploy and bug-discovery despite 3 passing retry-tests.
---

# Async-Context-Manager Retry Pattern

## The Iron Law

> If your retry-loop wraps `async with X:` instead of being wrapped BY it, your retry-logic is fictional for the most common transient-failure mode: connection-setup-timeout.

## The trap (concrete from E-7.3.3 03.06.2026)

### Wrong (heute Vormittag deployed E-7.3.2)

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
                # retry-Logik HIER drin
                await asyncio.sleep(delays[attempt])
except Exception as exc:             # ← catches __aenter__-TimedOut
    log.error("Unexpected send-error: %s", exc)
    return False                     # ← Zero retries done!
```

**Bug-Wirkung**: `Bot.__aenter__()` ruft `initialize()` mit HTTPX-Connection-Setup. Wenn diese TimedOut wirft, fliegt die Exception OUTSIDE des inneren retry-`try`, wird vom äußeren `except Exception` gefangen, und **Retry-Loop wird nie betreten** — auch wenn Retry-Logic vorhanden ist.

**Live-Beleg**: 6 Sekunden zwischen DB-Save und Error-Log. Echte 3-Retries mit Backoff [1s, 2s, 4s] + 4 × ~5s default-timeout = ~27 Sekunden. Differenz = Beweis dass kein Retry lief.

### Right

```python
last_exc = None
for attempt in range(MAX_RETRIES + 1):
    bot = create_bot(token)              # ← Fresh Bot-Instance pro Versuch
    try:
        async with bot:                  # ← __aenter__ JETZT im retry-Scope
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

Beachte:
1. `async with bot:` ist INNERHALB des `for attempt in range(...)`-Loops
2. Bot-Instance wird IN jedem Iteration neu erstellt — fresh Connection-Pool
3. Der `try/except TelegramError` umschließt jetzt sowohl `__aenter__` als auch `bot.send_message()` — beide Failure-Modi werden retry-klassifiziert

## Why this matters generally

Jedes der folgenden Patterns hat den gleichen Fehler-Pfad:

| Library | Risky `__aenter__` does |
|---|---|
| python-telegram-bot `async with Bot(...) as bot` | HTTPX-Client-Init, eventuell `initialize()` mit getMe() |
| httpx `async with AsyncClient(...) as c` | Transport-Setup, kann sich SSL-Handshakes verzögern |
| asyncpg `async with pool.acquire() as conn` | TCP-Handshake zum Postgres, TLS-Upgrade, Auth-Roundtrip |
| websockets `async with connect(url) as ws` | TCP + WS-Upgrade-Handshake |
| aiohttp `async with session.get(url) as resp` | Verbindung + Request + Initial-Response-Header |
| aiokafka `async with consumer:` | Broker-Connection + Group-Coordination |

Alle haben non-trivial IO in `__aenter__`. Wenn dein Retry-Loop außenrum sitzt, hast du sie nicht abgedeckt.

## Test-Plicht (heute aufgedeckt)

**Test-Lücke heute Vormittag**: alle 3 retry-Tests mockten `FakeBotClass.__aenter__` als trivialen Stub:
```python
class FakeBotClass:
    async def __aenter__(self): return self   # ← failt nie
    async def __aexit__(self, *a): return None
    async def send_message(self, **k): ...    # ← Test mockt nur DAS
```

Damit war der Test grün, aber der reale Failure-Modus (`__aenter__` wirft TimedOut) war komplett unabgedeckt.

**Fix-Test-Pattern**: mindestens EIN Test pro Library wo `__aenter__` selbst eine retryable Exception wirft:

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

Erwartung:
- `aenter_calls["n"] == 3` (2 failures + 1 success)
- `send_calls["n"] == 1` (send_message wird nur 1× erreicht — beim erfolgreichen attempt)
- `sleeps == [1.0, 2.0]` (2 backoffs zwischen den 3 attempts)

## The 4-Step Refactor Procedure

### Step 1 — Audit: was macht `__aenter__` wirklich?

Library-Docs lesen oder Source-Code:
- python-telegram-bot 22.x: `Bot.__aenter__` → `initialize()` → `httpx.AsyncClient` setup + optional `getMe()`-Call
- asyncpg: `pool.acquire().__aenter__` → connect + TLS + auth
- httpx: `AsyncClient.__aenter__` → in der Regel nur in-memory state aber `aclose` macht Connection-Pool-Drain

Wenn `__aenter__` Netz-IO macht: Retry-Scope einschließen.

### Step 2 — Refactor: Context-Manager IN den Loop

Vorher:
```python
async with X:
    for attempt in retries: try send except retry sleep
```

Nachher:
```python
for attempt in retries:
    X = create_fresh()        # ← optional: fresh resource pro versuch
    try:
        async with X:
            await operation()
        break
    except RetryableErr: sleep
    except NonRetryableErr: return
```

### Step 3 — RED-Test mit `__aenter__`-Failure

Schreibe einen Test wo `__aenter__` mehrfach failt. **Vor Fix muss er rot sein** — sonst hattest du das Bug-Pattern nicht.

### Step 4 — GREEN: Refactor anwenden, Test grün

Plus: bestehende „send-fails-but-aenter-ok"-Tests müssen weiterhin grün bleiben (Regression).

## Anti-patterns

- ❌ **„Mein Retry-Loop ist drin im async with"** — du retryst nur den Operations-Call, nicht den Setup. Connection-Setup-TimedOut fliegt durch.
- ❌ **Singleton-Resource im Retry-Loop** — wenn du EINE Bot-Instance verwendest und der Connection-State korrupt ist, retryst du gegen denselben kaputten State. Lösung: `create_fresh()` pro Iteration.
- ❌ **`except Exception` außerhalb des Retry-Loops** — fängt zu viel, maskiert Connection-Setup-Failures als „Unexpected". Wenn überhaupt: VOR dem Loop loggen + raise.
- ❌ **Test mockt `__aenter__` als trivialen Stub** — du testest dann nicht den heißen Pfad. Mindestens ein Test mit `__aenter__`-Failure.
- ❌ **Retry-Counter im Klassen-Attribute statt Closure** — beim Test mit mehreren Test-Cases im selben Process bleiben die Counter aus dem vorigen Test hängen. Pro-Test fresh-instance.

## Skill-Composition

- `superpowers:test-driven-development` — runs AROUND this skill (RED-Test mit __aenter__-Failure → GREEN-Refactor)
- `library-subclass-explicit-type-classification-DRAFT` — komplementärer Aspekt: WELCHE Exceptions sind retryable? Dieser hier: WO greift Retry?
- `forensik-spur-fuer-fire-and-forget-sends-DRAFT` — orthogonal: DB-Spur bei Send-Fail damit silent-Failure nicht silent bleibt
- `asyncpg-live-vs-mock-shape` — anderer Aspekt von Mock-vs-Live-Divergenz (Type-Coercion, nicht Context-Manager-Setup)

## When-Built / Why-Built

Built 03.06.2026 ~16:45 nach E-7.3.3 Forensik:

- 03.06. ~12:00 Wolf-Feedback dass heute Vormittag-Signal kein Advisory hatte
- 03.06. ~12:30 deployed E-7.3.2 Retry-Logik (alle 3 Tests grün)
- 03.06. ~14:02 nächstes Signal (BAS.DE LONG): DB-Save OK, Telegram-Send TimedOut → "Unexpected send-error", **kein Retry**
- 03.06. ~16:30 Wolf-Feedback: „wieder kein Advisory trotz Fix"
- 03.06. ~16:45 Forensik in journalctl, Root-Cause klar
- 03.06. ~17:00 RED-Test mit __aenter__-TimedOut → exakt der Production-Log-String
- 03.06. ~17:10 GREEN-Refactor: `async with bot` in den Loop verschoben, fresh Bot pro Versuch
- 03.06. ~17:25 Live-Verify mit nachträglichem Send für Assessment #145 → 200 OK, telegram_sent_at gesetzt

Bug-Lifetime: ~9 Stunden zwischen Deploy und Discovery, despite green tests. **Test-Pattern-Lücke** (triviale __aenter__-Mocks) war die strukturelle Ursache.

Promotion-Trigger: ≥2 weitere Live-Anwendungen außerhalb python-telegram-bot (z.B. asyncpg-pool-acquire Retry, httpx-Client-Setup Retry).
