---
name: lazy-module-getattr-for-settings-override
description: |-
  Use when a Python app needs user-editable runtime configuration that should OVERRIDE existing code constants without refactoring downstream callers. Triggers on phrases like "build settings form", "user should be able to change values", "without refactoring calc.py", "DB override above defaults", "inputs.py stays, but DB should take precedence", "how do we make the hardcoded values editable". Do NOT load for greenfield apps without existing code constants (then settings class from the start), for performance-critical hot paths where module-`__getattr__` would be a bottleneck, or when the values already go through dependency-injection (then refactor is minimal). Pattern: `inputs.py` remains as defaults, new `cfg.py` with module-level `__getattr__` (PEP 562) does lazy lookup to settings DB with 60s TTL cache, fallback to inputs.py. Callers import `from data import cfg as inputs` (1-line change) — calc.py + other consumers stay unchanged. Pattern derived from practice: applied successfully 2x in one day on two different apps.

---

# Lazy Module-`__getattr__` for Settings Override

> ⚠️ **DRAFT**. Pattern emerged from 2 sessions on the same day. TDD promotion cycle pending.

## The problem

A Python app has an `inputs.py` / `config.py` / `constants.py` with hardcoded values. Callers throughout the app use `from data import inputs` and `inputs.RENTENWERT_AKTUELL`. The user should now be able to **edit these values at runtime** (settings form, DB override) — but:

- **Refactor of 30+ caller sites** to a new API is expensive + risky
- **Settings class + dependency injection** would be architecturally clean, but breaks existing `inputs.XYZ` pattern
- **Direct overwrite of `inputs.py` via settings DB** doesn't work, because `inputs.py` is evaluated once at import

## Pattern (5 Steps)

### Step 1: `inputs.py` stays as defaults

No change. Stays as Single Source of Truth for initial seed of settings DB.

```python
# data/inputs.py — UNCHANGED
PENSION_VALUE_CURRENT_EUR = 42.52
CURRENT_SALARY_GROSS = 115_241.0
# ... 25+ constants
```

### Step 2: Settings DB + helper

```python
# data/settings_db.py
import sqlite3, time, threading
_CACHE: dict = {}
_CACHE_TS = 0.0
_CACHE_TTL = 60.0
_LOCK = threading.Lock()

def get_setting(key: str, default=None):
    global _CACHE, _CACHE_TS
    now = time.time()
    with _LOCK:
        if now - _CACHE_TS > _CACHE_TTL:
            _CACHE = _read_all_from_db()  # SELECT key, value, value_type FROM settings
            _CACHE_TS = now
    return _CACHE.get(key, default)

def update_setting(key: str, value):
    # UPDATE + invalidate cache
    ...
```

### Step 3: Lazy wrapper module with `__getattr__` (PEP 562)

```python
# data/cfg.py
from . import inputs
from . import settings_db

# Mapping: Python attribute → DB key
_OVERRIDE_MAP: dict[str, str] = {
    "PENSION_VALUE_CURRENT_EUR":   "pension.value",
    "CURRENT_SALARY_GROSS":  "user.current_salary_gross",
    # ... explicit whitelist only for editable values
}

def __getattr__(name: str):
    """Lazy lookup: first settings DB, then inputs.py default.

    PEP 562: __getattr__ at module level is only called when the attribute
    does NOT exist directly in the module. Since cfg.py defines no global
    constants, this function catches ALL accesses.
    """
    # 1. Override via settings DB?
    db_key = _OVERRIDE_MAP.get(name)
    if db_key is not None:
        db_value = settings_db.get_setting(db_key, default=None)
        if db_value is not None:
            return db_value
    # 2. Fallback to inputs.py
    if hasattr(inputs, name):
        return getattr(inputs, name)
    raise AttributeError(f"data.cfg has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(_OVERRIDE_MAP.keys()) + [n for n in dir(inputs) if not n.startswith("_")]))
```

### Step 4: 1-line change in main.py

```python
# Before
from data import inputs

# After
from data import cfg as inputs
```

**That's it.** All callers (calc.py, services, etc.) stay unchanged. `inputs.PENSION_VALUE_CURRENT_EUR` now goes through the lazy wrapper.

### Step 5: Tests + invalidation

```python
def test_cfg_falls_back_to_inputs_when_db_empty(monkeypatch):
    monkeypatch.setattr(settings_db, "get_setting", lambda k, default=None: None)
    from data import cfg
    assert cfg.PENSION_VALUE_CURRENT_EUR == inputs.PENSION_VALUE_CURRENT_EUR

def test_cfg_returns_db_override_when_set(monkeypatch):
    monkeypatch.setattr(settings_db, "get_setting",
        lambda k, default=None: 99.99 if k == "pension.value" else None)
    from data import cfg
    assert cfg.PENSION_VALUE_CURRENT_EUR == 99.99
```

## Why not other patterns?

| Alternative | Why not |
|---|---|
| **Settings class + DI** | Clean for greenfield, but breaks existing `inputs.XYZ` API. Refactor of 30+ callers. |
| **Override `inputs.py` via env vars** | Doesn't work for dynamic user-edits (app restart needed). |
| **Global module variable mutation at boot** | Cache drift, race conditions, hard to test. |
| **Direct DB calls in every caller** | Scattered DB connections, no caching. |
| **`importlib.reload(inputs)`** | Breaks existing in-memory references, race conditions. |

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| `cfg.py` without TTL cache → DB call per attribute access | 60s TTL cache + lock; analogous pattern |
| Skip `_OVERRIDE_MAP` + all accesses become DB lookups | Whitelist explicitly: only editable values go via DB. Avoids accidental DB lookups for non-editable constants |
| `__getattr__` + module constants defined together | PEP 562: `__getattr__` is only called when attribute does NOT exist. If `cfg.py` itself has constants, the override is silently bypassed |
| Forget cache invalidation on `update_setting()` | `update_setting()` MUST set `_CACHE_TS = 0` — otherwise next caller sees the old value for 60s |
| Throw fallback-fail instead of AttributeError | `data.cfg` is drop-in replacement for `data.inputs` — same error semantics (AttributeError for unknown attributes) |

## When the pattern does NOT fit

- **Greenfield apps** without existing `inputs.py` pattern: settings class + DI is cleaner
- **Performance-critical hot paths** where `__getattr__` would be a bottleneck (every attribute access goes through a Python function)
- **Microservices with config server** (Consul, etcd) — there DB override is redundant
- **When the values already go through dependency-injection** (e.g. FastAPI dependencies) — then refactor is minimal

## Real-world impact

**Session A** (morning, quarantine filter): needed dynamic `system_phase.mode` resolution with env override + DB lookup + fallback. 60s TTL cache, thread-safe. Callers (scheduler/jobs.py, scripts/quarantine_reeval.py) needed NO refactor.

**Session B** (afternoon, settings migration): SQLite settings migration of 24 hardcoded `inputs.py` constants. Same pattern: `__getattr__` + DB lookup + fallback. **calc.py (530 lines, 30+ inputs accesses) completely unchanged**. Only `main.py` 1 line (`from data import cfg as inputs`).

**Hypothetical — if this pattern had not been available**:
- Session B: would have required calc.py refactor + test adjustment (~2h)
- Session A: would have required explicit pass-through dependency-injection across 4-5 caller levels (~1h)
- **Total saved: ~3h** — per day-of-pattern-application

## Cross-References

- `enum-known-values-via-insert-grep` skill — complementary: read-side validation vs write-side override
- CLAUDE.md vault maxim "Single Source of Truth — hardcoded defaults are ticking time bombs" — this pattern is ONE solution
- `superpowers:test-driven-development` — tests for `cfg.py` are essential because module `__getattr__` is subtle to debug

## TDD promotion backlog (Cycle 1, pending)

- RED subagent without skill: would likely suggest settings class + DI → 30+ caller refactor
- GREEN subagent with skill: would lay out `cfg.py` with `__getattr__` + 1-line change in main.py
- Refactor expectation: Step 5 (tests) could be more detailed; edge cases (`hasattr()` with __getattr__ modules)
- Cycle 1 to be scheduled when next settings migration arises
