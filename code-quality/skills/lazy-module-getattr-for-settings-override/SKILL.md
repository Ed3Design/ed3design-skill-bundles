---
name: lazy-module-getattr-for-settings-override-DRAFT
description: STUB — Use when a Python app needs user-editable runtime configuration that should OVERRIDE existing code constants without refactoring downstream callers. Triggers on phrases like "Settings-Form bauen", "User soll Werte ändern können", "ohne calc.py zu refactoren", "DB-Override über Defaults", "inputs.py bleibt, aber DB soll Vorrang haben", "wie machen wir die hardcoded Werte editierbar". Do NOT load for greenfield-Apps ohne existing Code-Konstanten (dann Settings-Klasse von Anfang an), für Performance-kritische Hot-Paths wo Modul-`__getattr__` ein Bottleneck wäre, oder wenn die Werte bereits über dependency-injection gehen (dann ist Refactor minimal). Pattern: `inputs.py` bleibt als Defaults, neues `cfg.py` mit Modul-level `__getattr__` (PEP 562) macht Lazy-Lookup zu Settings-DB mit 60s-TTL-Cache, Fallback auf inputs.py. Caller importieren `from data import cfg as inputs` (1-Zeilen-Change) — calc.py + andere Verbraucher bleiben unverändert. Wolf-Erlebnis 11.06.2026: vt_source.py (Vormittag, ultimative-platform Quarantine-Filter) + absprung cfg.py (Nachmittag, Settings-Form) — gleicher Pattern 2× am selben Tag erfolgreich appliziert.
---

# Lazy Module-`__getattr__` für Settings-Override

> ⚠️ **DRAFT — Stand 11.06.2026**. Pattern aus 2 Sessions am gleichen Tag entstanden. TDD-Promotion-Cycle steht aus.

## Das Problem

Eine Python-App hat eine `inputs.py` / `config.py` / `constants.py` mit hardcoded Werten. Caller in der ganzen App nutzen `from data import inputs` und `inputs.RENTENWERT_AKTUELL`. User soll diese Werte jetzt **runtime editieren** können (Settings-Form, DB-Override) — aber:

- **Refactor von 30+ Caller-Stellen** auf neue API ist teuer + risk
- **Settings-Klasse + Dependency-Injection** würde architektonisch sauber sein, aber bricht existing `inputs.XYZ`-Pattern
- **Direkt `inputs.py` per Settings-DB überschreiben** geht nicht, weil `inputs.py` beim Import einmal evaluiert wird

## Pattern (5 Steps)

### Step 1: `inputs.py` bleibt als Defaults

Keine Änderung. Bleibt Single Source of Truth für Erst-Seed der Settings-DB.

```python
# data/inputs.py — UNVERÄNDERT
RENTENWERT_AKTUELL_EUR = 42.52
AKTUELLES_GEHALT_BRUTTO = 115_241.0
# ... 25+ Konstanten
```

### Step 2: Settings-DB + Helper

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

### Step 3: Lazy-Wrapper-Modul mit `__getattr__` (PEP 562)

```python
# data/cfg.py
from . import inputs
from . import settings_db

# Mapping: Python-Attribut → DB-Key
_OVERRIDE_MAP: dict[str, str] = {
    "RENTENWERT_AKTUELL_EUR":   "drv.rentenwert",
    "AKTUELLES_GEHALT_BRUTTO":  "wolf.aktuelles_gehalt_brutto",
    # ... explizite Whitelist nur für editierbare Werte
}

def __getattr__(name: str):
    """Lazy-Lookup: erst Settings-DB, dann inputs.py-Default.

    PEP 562: __getattr__ auf Modulebene wird nur aufgerufen wenn das Attribut
    NICHT direkt im Modul existiert. Da cfg.py keine globalen Konstanten
    definiert, fängt diese Funktion ALLE Zugriffe.
    """
    # 1. Override via Settings-DB?
    db_key = _OVERRIDE_MAP.get(name)
    if db_key is not None:
        db_value = settings_db.get_setting(db_key, default=None)
        if db_value is not None:
            return db_value
    # 2. Fallback auf inputs.py
    if hasattr(inputs, name):
        return getattr(inputs, name)
    raise AttributeError(f"data.cfg hat kein Attribut {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(_OVERRIDE_MAP.keys()) + [n for n in dir(inputs) if not n.startswith("_")]))
```

### Step 4: 1-Zeilen-Change in main.py

```python
# Vorher
from data import inputs

# Nachher
from data import cfg as inputs
```

**Das war's.** Alle Caller (calc.py, services, etc.) bleiben unverändert. `inputs.RENTENWERT_AKTUELL_EUR` geht jetzt durch den Lazy-Wrapper.

### Step 5: Tests + Invalidation

```python
def test_cfg_falls_back_to_inputs_when_db_empty(monkeypatch):
    monkeypatch.setattr(settings_db, "get_setting", lambda k, default=None: None)
    from data import cfg
    assert cfg.RENTENWERT_AKTUELL_EUR == inputs.RENTENWERT_AKTUELL_EUR

def test_cfg_returns_db_override_when_set(monkeypatch):
    monkeypatch.setattr(settings_db, "get_setting",
        lambda k, default=None: 99.99 if k == "drv.rentenwert" else None)
    from data import cfg
    assert cfg.RENTENWERT_AKTUELL_EUR == 99.99
```

## Warum nicht andere Patterns?

| Alternative | Warum nicht |
|---|---|
| **Settings-Klasse + DI** | Sauber bei Greenfield, aber bricht existing `inputs.XYZ`-API. Refactor von 30+ Callern. |
| **`inputs.py` per ENV-Vars überschreiben** | Geht nicht für dynamische User-Edits (App-Restart nötig). |
| **Globale Modul-Variable-Mutation beim Boot** | Cache-Drift, Race-Conditions, schwer testbar. |
| **Direkte DB-Calls in jedem Caller** | Verstreute DB-Connections, kein Caching. |
| **`importlib.reload(inputs)`** | Bricht existing in-Memory-Referenzen, race-conditions. |

## Anti-Patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| `cfg.py` ohne TTL-Cache → DB-Call pro Attribut-Zugriff | 60s-TTL-Cache + Lock; analog `vt_source.py`-Pattern |
| `_OVERRIDE_MAP` weglassen + alle Zugriffe DB-Lookup | Whitelist explizit: nur editierbare Werte gehen über DB. Vermeidet versehentliche DB-Lookups für nicht-editierbare Konstanten |
| `__getattr__` zusätzlich Modul-Konstanten definieren | PEP 562: `__getattr__` wird nur aufgerufen wenn Attribut NICHT existiert. Wenn `cfg.py` selbst Konstanten hat, wird der Override stumm umgangen |
| Cache-Invalidation vergessen bei `update_setting()` | `update_setting()` MUSS `_CACHE_TS = 0` setzen — sonst sieht der nächste Caller für 60s den alten Wert |
| Fallback-fail werfen statt AttributeError | `data.cfg` ist Drop-in-Replacement für `data.inputs` — gleiche Fehler-Semantik (AttributeError für unbekannte Attribute) |

## Wann das Pattern NICHT trifft

- **Greenfield-Apps** ohne existing `inputs.py`-Pattern: Settings-Klasse + DI ist sauberer
- **Performance-kritische Hot-Paths** wo `__getattr__` ein Bottleneck wäre (jeder Attribut-Zugriff geht durch Python-Function)
- **Microservices mit Config-Server** (Consul, etcd) — dort ist DB-Override redundant
- **Wenn die Werte schon über dependency-injection** gehen (z.B. FastAPI-Dependencies) — dann ist Refactor minimal

## Real-World-Impact

**11.06.2026 ultimative-platform `vt_source.py`** (Vormittag): Quarantine-Filter brauchte dynamische `system_phase.mode`-Auflösung mit Env-Override + DB-Lookup + Fallback. 60s-TTL-Cache, Thread-Safe. Caller (scheduler/jobs.py, scripts/quarantine_reeval.py) brauchten KEINEN Refactor.

**11.06.2026 absprung `cfg.py`** (Nachmittag): SQLite-Settings-Migration von 24 hardcoded `inputs.py`-Konstanten. Gleicher Pattern: `__getattr__` + DB-Lookup + Fallback. **calc.py (530 Zeilen, 30+ inputs-Zugriffe) komplett unverändert**. Nur `main.py` 1 Zeile (`from data import cfg as inputs`).

**Hypothetisch — wenn dieses Pattern nicht verfügbar gewesen wäre**:
- absprung: hätte calc.py-Refactor + Tests-Anpassung gebraucht (~2h)
- vt_source: hätte explizite Pass-Through-Dependency-Injection durch 4-5 Caller-Levels gebraucht (~1h)
- **Total gespart: ~3h** — pro Day-of-Pattern-Application

## Cross-References

- `enum-known-values-via-insert-grep` Skill — komplementär: Read-Side-Validation vs Write-Side-Override
- CLAUDE.md Vault-Maxime „Single Source of Truth — Hardcoded-Defaults sind tickende Bomben" — dieses Pattern ist EINE Lösung dafür
- `superpowers:test-driven-development` — Tests für `cfg.py` sind essentiell weil Modul-`__getattr__` subtil zu debuggen ist

## TDD-Promotion-Backlog (Cycle 1, steht aus)

- RED-Subagent ohne Skill: würde wahrscheinlich Settings-Klasse + DI vorschlagen → 30+ Caller-Refactor
- GREEN-Subagent mit Skill: würde `cfg.py` mit `__getattr__` anlegen + 1-Zeilen-Change in main.py
- Refactor-Erwartung: Step 5 (Tests) könnte detaillierter sein; Edge-Cases (`hasattr()` mit __getattr__-Modulen)
- Cycle 1 zu planen wenn nächste Settings-Migration ansteht (z.B. pvista oder hausverwaltung)
