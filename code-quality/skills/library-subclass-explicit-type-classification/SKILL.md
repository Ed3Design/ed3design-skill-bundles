---
name: library-subclass-explicit-type-classification
description: Use when classifying exceptions or other library-provided objects by type AND the semantically-distinct behaviors map onto a class-hierarchy where subclasses inherit from a base that has DIFFERENT desired handling. Common in retry-logic for HTTP clients (requests/httpx/urllib3 — Timeout vs HTTPError vs ConnectionError vs subclass), Telegram bots (python-telegram-bot — BadRequest inherits from NetworkError but should NOT be treated as a network issue), SQL clients (psycopg/asyncpg — OperationalError vs ProgrammingError vs subclass), file I/O (FileNotFoundError vs PermissionError vs OSError). Trigger on phrases like "retry logic for TelegramError", "isinstance vs type()", "retry classification", "exception type check", "BadRequest inherits from NetworkError", "subclass trap", "HTTPError vs Timeout", "retry strategy for library X". The skill produces (1) class-hierarchy mapping (literal `mro()` check), (2) explicit type-classification helper, (3) tests that lock the distinction. Do NOT load when all exceptions of a hierarchy should be handled identically (then base-class isinstance is correct), when the library docs explicitly state "always catch base class" (e.g. some SDKs flatten error semantics), or for first-time exception-handling design without prior library-hierarchy experience (use general try/except pattern first). Encodes a real trap: BadRequest inherits from NetworkError in python-telegram-bot 22.x → naive `isinstance(exc, NetworkError)` as retry condition would retry Markdown issues 3x instead of failing fast. Solution: `type(exc) is NetworkError` (exact type check).

---

# Library-Subclass Explicit Type Classification

## Overview

Some library exception/object hierarchies have subclasses with semantically-distinct desired handling, but the parent class catches them via `isinstance`. Naive code that classifies by `isinstance(exc, BaseClass)` gets it wrong.

**Core principle:** When behavior diverges between parent and child of a class-hierarchy, use `type(obj) is X` (exact match) instead of `isinstance(obj, X)`.

## The trap (concrete examples)

### Python-Telegram-Bot 22.x

```python
TelegramError
├── NetworkError              ← "transient, retryable"
│   ├── TimedOut              ← retryable
│   └── BadRequest            ← NOT retryable (Markdown issue, wrong chat_id)
├── RetryAfter                ← retryable, wait exc.retry_after
└── Forbidden                 ← NOT retryable (bot blocked)
```

`isinstance(exc, NetworkError)` matched BadRequest. Wrong for retry logic.

### Requests / HTTPX

```python
RequestException
├── ConnectionError           ← retryable
│   ├── ConnectTimeout        ← retryable
│   └── SSLError              ← NOT retryable (cert problem, won't fix on retry)
├── Timeout
│   └── ReadTimeout           ← retryable
│   └── ConnectTimeout
└── HTTPError                 ← NOT retryable (4xx response)
```

`isinstance(exc, ConnectionError)` matched SSLError.

### Psycopg / SQLAlchemy

```python
Error
├── OperationalError          ← maybe-retryable (connection lost)
│   ├── DeadlockDetected      ← retryable
│   └── DataError-Subclass    ← NOT retryable (bad data)
└── ProgrammingError          ← NOT retryable (SQL bug)
```

## The 5-step procedure

### Step 1 — List the class hierarchy with `__mro__`

```python
from telegram.error import BadRequest
print([b.__name__ for b in BadRequest.__mro__])
# ['BadRequest', 'NetworkError', 'TelegramError', 'Exception', 'BaseException', 'object']
```

**Mandatory** before writing classification logic — library doc claims are often incomplete.

### Step 2 — Identify the semantic divergence

For each subclass:
- What is the user-action recommendation from the library (docs)?
- What is the code-action necessity from your code?
- Which subclass sets have semantically identical actions?

### Step 3 — Write explicit classification helper

```python
def _is_retryable_telegram_error(exc: Exception) -> bool:
    """Classifies TelegramError.

    Important: BadRequest inherits from NetworkError. We check by type(),
    NOT via isinstance(NetworkError) — that matches BadRequest too.
    """
    from telegram.error import TimedOut, RetryAfter, NetworkError
    if isinstance(exc, (TimedOut, RetryAfter)):
        return True
    if type(exc) is NetworkError:  # EXACT type, no subclasses
        return True
    return False
```

**Pattern**: tuple-isinstance for subclass families that are handled identically, `type() is X` for base-class match without subclasses.

### Step 4 — Lock the distinction with TDD

```python
def test_bad_request_is_not_retryable():
    """BadRequest inherits from NetworkError → naive isinstance would classify
    BadRequest as retryable. Verifies that type() check distinguishes."""
    from telegram.error import BadRequest
    assert _is_retryable_telegram_error(BadRequest("test")) is False

def test_network_error_is_retryable():
    """NetworkError itself (without subclass) is retryable."""
    from telegram.error import NetworkError
    assert _is_retryable_telegram_error(NetworkError("test")) is True
```

Both tests are needed — the first locks against refactoring slip, the second against accidental under-classification.

### Step 5 — Document the hierarchy pitfall in code comments

Future developers MUST understand the reason for `type() is X`, otherwise they will naively refactor it back to `isinstance`. In the docstring + next to the check.

## Anti-patterns

- ❌ **Naive `isinstance(exc, NetworkError)`** as retry condition — matches subclasses with different semantics
- ❌ **Catch-all `except TelegramError`** as classification layer — loses the distinction completely
- ❌ **No MRO check** before classification — assumptions about hierarchy are often wrong (e.g. one thinks BadRequest inherits directly from TelegramError, but it doesn't)
- ❌ **`type() ==` instead of `type() is`** — works here too but `is` is convention for identity check with type objects
- ❌ **Hardcoded subclass list without test** — when the library hierarchy changes, you don't know that the classification is stale

## Quick-Check routine

When is this skill relevant?

1. You're building retry/fallback/special-handling logic for an external library
2. Library docs classify errors by class
3. You catch yourself using `isinstance(exc, SomeBaseClass)` as a retry gate
4. → Stop. Check MRO of the subclasses, classify explicitly.

## Worked example

User-driven forensics: an Advisor-Send didn't arrive. Live reproduction with log.error caught `Timed out`. Naive retry implementation:

```python
# Naive (WRONG):
if isinstance(exc, NetworkError):  # matched BadRequest!
    retry()
```

Would have led to: every BadRequest (e.g. Markdown parse error) would be retried 3x. 3x same fail, 3x exponential backoff = 7s wait for nothing, plus delay of other tasks.

Correct classification:
```python
if isinstance(exc, (TimedOut, RetryAfter)):
    retry()
elif type(exc) is NetworkError:  # EXACT
    retry()
else:
    fail_fast()
```

Tests: `no_retry_on_bad_request` verified that BadRequest stays single-attempt.

## Skill composition

- `superpowers:test-driven-development` — for the tests that lock the classification
- `superpowers:systematic-debugging` — when the bug "retry behaves wrong" is found via systematic-debugging

## Library notes (verified pitfalls)

| Library | Pitfall |
|---|---|
| `python-telegram-bot` 22.x | `BadRequest` inherits from `NetworkError` |
| `requests` | `SSLError` inherits from `ConnectionError` (not retryable) |
| `httpx` | `HTTPStatusError` separate from `RequestError` (different from requests) |
| `psycopg` | `DeadlockDetected` inherits from `OperationalError` (retryable) vs other `OperationalError` subclasses (not) |
| `boto3` | `ClientError` classified per `error['Code']` — not per subclass |

For every new library: `print([b.__name__ for b in YourException.__mro__])` first.
