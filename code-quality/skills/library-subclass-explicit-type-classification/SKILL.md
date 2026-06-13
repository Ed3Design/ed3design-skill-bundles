---
name: library-subclass-explicit-type-classification
description: Use when classifying exceptions or other library-provided objects by type AND the semantically-distinct behaviors map onto a class-hierarchy where subclasses inherit from a base that has DIFFERENT desired handling. Common in retry-logic for HTTP clients (requests/httpx/urllib3 — Timeout vs HTTPError vs ConnectionError vs subclass), Telegram bots (python-telegram-bot — BadRequest erbt von NetworkError aber soll NICHT als Network-Issue behandelt werden), SQL clients (psycopg/asyncpg — OperationalError vs ProgrammingError vs subclass), file I/O (FileNotFoundError vs PermissionError vs OSError). Trigger on phrases like "Retry-Logik für TelegramError", "isinstance vs type()", "retry classification", "exception type check", "BadRequest erbt von NetworkError", "Subclass-Falle", "HTTPError vs Timeout", "retry strategy bei Lib X". The skill produces (1) class-hierarchy-mapping (literal `mro()`-Check), (2) explicit type-classification helper, (3) tests that lock the distinction. Do NOT load when all exceptions of a hierarchy should be handled identically (then base-class isinstance is correct), when the library docs explicitly state "always catch base class" (e.g. some SDKs flatten error semantics), or for first-time exception-handling design without prior library-hierarchy-experience (use general try/except-pattern first). Encodes the 03.06.2026 ultimative-platform E-7.3.2 trap: BadRequest erbt von NetworkError in python-telegram-bot 22.x → naives `isinstance(exc, NetworkError)` als Retry-Bedingung würde Markdown-Issues 3× retryen statt fail-fast. Lösung: `type(exc) is NetworkError` (exakter Typ-Check).
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
│   └── BadRequest            ← NOT retryable (Markdown-Issue, falsche chat_id)
├── RetryAfter                ← retryable, wait exc.retry_after
└── Forbidden                 ← NOT retryable (bot blocked)
```

`isinstance(exc, NetworkError)` matched BadRequest. Falsch für Retry-Logic.

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
└── ProgrammingError          ← NOT retryable (SQL-Bug)
```

## The 5-step procedure

### Step 1 — Liste die Klassen-Hierarchie mit `__mro__`

```python
from telegram.error import BadRequest
print([b.__name__ for b in BadRequest.__mro__])
# ['BadRequest', 'NetworkError', 'TelegramError', 'Exception', 'BaseException', 'object']
```

**Mandatory** before writing classification logic — Library-Doku-Behauptungen sind oft unvollständig.

### Step 2 — Identifiziere die Semantic-Divergence

Für jede Subclass:
- Was ist die User-Action-Empfehlung von der Library (Doku)?
- Was ist die Code-Action-Notwendigkeit von deinem Code?
- Welche Subclass-Sets haben semantisch identische Aktionen?

### Step 3 — Schreibe explizite Klassifikations-Helper

```python
def _is_retryable_telegram_error(exc: Exception) -> bool:
    """Klassifiziert TelegramError.

    Wichtig: BadRequest erbt von NetworkError. Wir prüfen per type(),
    NICHT via isinstance(NetworkError) — das matched BadRequest auch.
    """
    from telegram.error import TimedOut, RetryAfter, NetworkError
    if isinstance(exc, (TimedOut, RetryAfter)):
        return True
    if type(exc) is NetworkError:  # EXAKTER Typ, keine Subclasses
        return True
    return False
```

**Pattern**: Tuple-isinstance für Subclass-Familien die identisch behandelt werden, `type() is X` für base-class-Match ohne Subclasses.

### Step 4 — Lock the distinction with TDD

```python
def test_bad_request_is_not_retryable():
    """BadRequest erbt von NetworkError → naives isinstance würde BadRequest
    als retryable einstufen. Verifiziert dass type()-Check unterscheidet."""
    from telegram.error import BadRequest
    assert _is_retryable_telegram_error(BadRequest("test")) is False

def test_network_error_is_retryable():
    """NetworkError selbst (ohne Subclass) ist retryable."""
    from telegram.error import NetworkError
    assert _is_retryable_telegram_error(NetworkError("test")) is True
```

Beide Tests sind nötig — der erste lockt gegen Refactoring-Slip, der zweite gegen accidentelle Unterstrike-Klassifikation.

### Step 5 — Document the Hierarchy-Pitfall in Code-Comment

Zukünftige Entwickler MÜSSEN den Grund für `type() is X` verstehen, sonst refactoren sie es naiv zurück zu `isinstance`. Im Docstring + neben dem Check.

## Anti-patterns

- ❌ **Naives `isinstance(exc, NetworkError)`** als Retry-Bedingung — matched Subclasses mit anderer Semantik
- ❌ **Catch-all `except TelegramError`** als Klassifikation-Layer — verliert die Distinction komplett
- ❌ **Keine MRO-Prüfung** vor der Klassifikation — Annahmen über Hierarchie sind oft falsch (z.B. man denkt BadRequest erbt direkt von TelegramError, tut es aber nicht)
- ❌ **`type() ==` statt `type() is`** — funktioniert hier auch aber `is` ist Convention für identity-check bei type-objects
- ❌ **Subclass-Liste hardcoden ohne Test** — wenn die Library-Hierarchie sich ändert, weiß man nicht dass die Klassifikation veraltet ist

## Quick-Check-Routine

Wann ist dieser Skill relevant?

1. Du baust Retry-/Fallback-/Special-Handling-Logic für eine externe Library
2. Library-Doku klassifiziert Errors per Klasse
3. Du erwischst dich bei `isinstance(exc, SomeBaseClass)` als Retry-Gate
4. → Stop. Prüfe MRO der Subclasses, klassifiziere explizit.

## Worked example (03.06.2026 — E-7.3.2)

Wolf-Forensik: heute morgen 06:02 UTC Advisor-Sends nicht angekommen. Live-Reproduktion mit log.error fing `Timed out` ab. Naive Retry-Implementation:

```python
# Naiv (FALSCH):
if isinstance(exc, NetworkError):  # matched BadRequest!
    retry()
```

Hätte dazu geführt: jeder BadRequest (z.B. Markdown-Parse-Fehler) würde 3× retryed werden. 3× same fail, 3× exponential backoff = 7s Wartezeit für nichts, plus Verzögerung anderer Tasks.

Korrekte Klassifikation:
```python
if isinstance(exc, (TimedOut, RetryAfter)):
    retry()
elif type(exc) is NetworkError:  # EXAKT
    retry()
else:
    fail_fast()
```

Tests: `no_retry_on_bad_request` verifizierte dass BadRequest single-attempt bleibt.

## Skill-Composition

- `superpowers:test-driven-development` — für die Tests die die Klassifikation locken
- `superpowers:systematic-debugging` — wenn der Bug "Retry verhält sich falsch" über systematic-debugging gefunden wird

## Library-Notes (verifizierte Pitfalls)

| Library | Pitfall |
|---|---|
| `python-telegram-bot` 22.x | `BadRequest` erbt von `NetworkError` |
| `requests` | `SSLError` erbt von `ConnectionError` (nicht retryable) |
| `httpx` | `HTTPStatusError` separat von `RequestError` (anders als requests) |
| `psycopg` | `DeadlockDetected` erbt von `OperationalError` (retryable) vs andere `OperationalError`-Subclasses (nicht) |
| `boto3` | `ClientError` per `error['Code']` klassifiziert — nicht per Subclass |

Bei jeder neuen Library: `print([b.__name__ for b in YourException.__mro__])` zuerst.
