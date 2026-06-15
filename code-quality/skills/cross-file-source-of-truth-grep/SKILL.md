---
name: cross-file-source-of-truth-grep
description: |-
  Use when you are about to refactor a value, constant, helper-function, lookup, or config-pattern from old-form to new-form across the codebase — schema-drift fixes ("`yf_symbol` → `symbol`"), display-name SoT migration ("inline-dict → `core/utils/display.instrument_label`"), config-pattern updates ("hardcoded VRM-ID → env-var"), helper-function rename, deprecated-import cleanup. STOP and run `grep -r "<old-pattern>"` on the WHOLE repo (not just the files you have open) BEFORE writing the new pattern anywhere. Specifically trigger when (a) you write phrases like "I'm refactoring X to Y", "fix schema drift in Y", "migrate from old to new form", "rename helper", "extract config default", "display-name single-source-of-truth", (b) you have a mental model "the 3 files that use this" or "only in /core/ relevant" — especially dispatcher / scheduler / jobs / notifications / tests often hide 1-2 additional places, (c) the new pattern is in production code but you haven't checked notification-dispatcher, scheduler-jobs, batch-scripts, integration-tests, mock-fixtures. Experience from practice: `notifications/signal_dispatcher.py:_get_display_name` still called the old `config_loader` path although the main path had been migrated — would have stayed undetected for weeks in the signal Telegram dispatch. Method: `grep -rn "<old-pattern>" --include="*.py"` excluding `node_modules`, `.git`, `*.pyc`, `__pycache__`, then read each hit line + categorize (production / notification / scheduler / test / mock / deprecated). Do NOT load for greenfield code (no old pattern to migrate from), for renames that are pure cosmetics with no semantic shift (e. g. variable in same file), for refactors that are guaranteed file-local (private helper in a single module). Complements `pre-deploy-code-drift-detection` (this skill catches drift BEFORE the refactor, that one catches drift AFTER the refactor); complement to `silent-except-versteckt-schema-drift` (which finds the same kind of dormant bug from the symptom side).

---

# Cross-File Source-of-Truth Grep

> ✅ **PROMOTED** — TDD Cycle 1 PASS. RED subagent gave a heuristic "grep first" recommendation, but without the decisive 4th grep pass on mapping values. GREEN subagent added the 4th pass `grep -rn "'CL=F'\s*:\s*'WTI"` — which catches copies of the mapping structure under deviating variable names (`_DISPLAY_MAP`, `LABELS`, dicts embedded inside helper functions). Precisely this pass would have caught the `signal_dispatcher.py:_get_display_name` bug before the refactor. **R1 refactor applied**: 4th grep pass in Quick Reference as a separate line + hint block.

## Overview

**Before every refactor: grep -r for the OLD pattern, not the NEW one.**

When you replace an old pattern (column name, helper call, inline dict, default string, deprecated import) with a new one, **2-5 additional callers** often lurk that you didn't have in the mental model of "the 3 relevant files":

- `notifications/` dispatcher (Telegram, email, webhook)
- Scheduler jobs (cron-triggered, often rarely touched)
- Batch scripts (offline analytics)
- Integration tests + mock fixtures
- Deprecated-but-still-in-path modules

Skill = simple discipline: **`grep -rn "<old-pattern>"` BEFORE you write the first new call.** 30 seconds of effort prevents hours of re-review cycle.

This maxim is the refactor-variant of the "Single Source of Truth" maxim: the SoT migration is only complete when grep for the old pattern returns nothing.

## When to use

**Trigger phrases (the kind you'd be about to use)**:
- "I'm refactoring <X> to <Y>"
- "fix schema drift in <table>.<column>"
- "introduce SoT for <Display-Name / config-var / helper>"
- "migrate from old `config_loader` path to new"
- "rename helper-function from foo to bar"
- "deprecated import cleanup"
- "extract config defaults from code"

**High-risk markers** (additional trigger):
- You have a small list of affected files in mind (≤5) — precisely then grep, because that's the case most prone to under-estimation
- The new pattern already lives somewhere ("we standardized this in `core/`") — meaning older spots are not migrated yet
- Module belongs to **notification / dispatcher / scheduler / cron / batch** — these paths are rarely touched, drift accumulates

## When NOT to use

- **Greenfield code**: the old pattern doesn't exist yet
- **Pure cosmetic rename in a single file**: local variable, no semantic shift
- **Guaranteed file-local helper**: `_private_helper` in module, with `_` prefix convention
- **Rename of a symbol with IDE refactor-tool**: when LSP refactor cleanly covers all callers, grep is redundant (but verify 1× **afterwards** anyway)

## The 4-Step Cross-File SoT Grep Flow

### Step 1 — Note the old pattern explicitly

Before grep, write as a comment or via TodoWrite:
- **Old pattern**: `o.yf_symbol` (column alias)
- **New pattern**: `o.symbol AS yf_symbol`
- **Suspected caller count**: 3 (`signals.py`, `timeline.py`, `take_signal`)
- **What I expect to find**: 3-5 (with ~2 extra in tests/mocks)

### Step 2 — Grep with repo scope

```bash
# Standard: all Python files incl. tests, scripts, integrations
grep -rn "<old-pattern>" --include="*.py" \
  --exclude-dir=node_modules \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=.venv \
  | grep -v "\.pyc:"
```

**Never** just in a subdirectory (`grep ... /core/`). That misses the skill's goal.

### Step 3 — Categorize the hit list

Sort each hit into one of these categories:

| Category | Example | Action |
|---|---|---|
| **Production hot-path** | `core/services/X.py` | migrate (mandatory) |
| **Production cold-path** | `notifications/dispatcher.py`, `scheduler/jobs/Y.py` | **migrate** + pre-push hook live-smoke if possible |
| **Test/Mock** | `tests/integration/test_Y.py` with fixed data | migrate + fixture updates |
| **Doc / Comment / Note** | `# old: yf_symbol` | leave as-is (history) OR replace if fully-replace required |
| **Deprecated-but-in-path** | `legacy/foo.py` with import from production | **explicitly decide**: migrate OR add deprecation notice + issue |
| **False positive** | substring match in variable name | ignore |

### Step 4 — Migrate + verification grep

After the refactor: **grep again `grep -rn "<old-pattern>"`** — result should be empty (or only the doc/comment false-positives remain).

```bash
grep -rn "<old-pattern>" --include="*.py" | wc -l
# Expectation: 0 (or list of deliberately not-migrated hits)
```

## Quick Reference

| Refactor type | Grep pattern (example) |
|---|---|
| Column rename | `grep -rn "\.yf_symbol\\|yf_symbol AS"` |
| Helper rename | `grep -rn "from .* import old_helper\\|old_helper("` |
| Inline-dict → SoT (variable name) | `grep -rn "display_names\\s*=\\s*{"` |
| **Inline-dict → SoT (value substring, catches obscured names)** | **`grep -rn "'CL=F'\\s*:\\s*'WTI"` — catches `_DISPLAY_MAP`, `LABELS`, `SYMBOL_NAMES` etc. which copy the same mapping under another name** |
| Deprecated import | `grep -rn "from config_loader import"` |
| Hardcoded env default | `grep -rn '"c0619ab1e363"\\|"my-host"'` (example values) |
| Magic string → enum | `grep -rn "'long'\\|'short'" --include="*.py"` |

> **R1 refactor (Cycle 1)**: the substring-grep on mapping **values** (`'CL=F': 'WTI`) is the most critical variant — it finds copies of the mapping structure under deviating variable names. Precisely this variant would have caught the `signal_dispatcher.py:_get_display_name` bug BEFORE the refactor (the dict there was not named `display_names` but was embedded in a helper function).

## Anti-Patterns

| Anti-Pattern | Lesson |
|---|---|
| "I know the 3 files that use this" | Mental models overlook notification/scheduler/batch — grep is 30s, less than the re-review cycle |
| Only grep in `core/` | Notification dispatcher often lies in `notifications/`, scheduler jobs in `scheduler/jobs/` — grep repo-wide |
| Grep without `--include="*.py"` | Hits in `.pyc`, `.log`, `node_modules` noise the output |
| Don't grep again after refactor | Verification grep is the final check — empty output = migration complete |
| Trust LSP refactor blindly | LSP usually finds everything, but dynamic imports (`importlib`) and string keys (`getattr(o, "yf_symbol")`) escape — grep finds both |

## Cost of Skipping (real)

**Experience from a Phase-1 re-review** (code-review cleanup):
- Display-name SoT migration to `core/utils/display.instrument_label()` had covered 4 hot-path files
- Re-review subagent found `notifications/signal_dispatcher.py:_get_display_name` with old `config_loader` path
- Would have stayed **unnoticed for weeks** in the V1/V2 signal Telegram dispatch — symbols in Telegram instead of display names

**Pattern**: notification-dispatcher modules are rarely touched + often have their own helper versions that are not visible in the main refactor path.

**Lesson**: 30s grep upfront = hours of re-review cycle saved.

## Red Flags — STOP and grep

- You're writing the first new call after a refactor right now
- Your mental model is "the 3 files" or "only in /core/"
- Notification/scheduler/batch were **not** explicitly mentioned in your list
- LSP refactor ran cleanly, but you have dynamic imports in the codebase

**All mean: 30s repo-wide grep on old pattern, then categorize hit list, then migrate.**

## Cross-References

- **REQUIRED COMPLEMENT**: `pre-deploy-code-drift-detection` (drift check AFTER the refactor)
- **COMPLEMENT**: `silent-except-versteckt-schema-drift` (same bug class from the symptom side)
- Maxim: "Single Source of Truth — hardcoded defaults are ticking time bombs"

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS with R1 refactor

- **RED subagent** (without skill, scenario "migrate display_names inline-dicts to central `instrument_label()`, 3 known files"): heuristically recommended "first grep for further occurrences" — surprisingly good, but **only the variable-name grep** (`grep -rn "display_names"`). Self-critique listed 7 points (repo not inspected, DB as SoT not addressed, migration order with imports, tests before deletion, tooling hint, anti-pattern arc, no dict diff before merge).

- **GREEN subagent** (with skill): brought the decisive added value — the **4th grep pass on mapping values** (`grep -rn "'CL=F'\s*:\s*'WTI"`) that catches copies of the mapping structure under deviating variable names. Plus: named concrete high-risk paths for the codebase (`notifications/signal_dispatcher.py`, `notifications/telegram_*.py`, `scheduler/jobs/*.py`, `briefings/*.py`), cross-reference to `pre-deploy-code-drift-detection` as complement after the refactor, schema-use-case-mismatch hint (`display_name IS NULL` check).

- **R1 refactor applied**: Quick Reference table extended with row "Inline-dict → SoT (value substring, catches obscured names)" + hint block that this is the most critical variant (would have caught the bug).

- **Anti-pattern avoided**: GREEN predicted the bug exactly — `notifications/signal_dispatcher.py` with its own `_get_display_name` would have stayed unmigrated, raw symbols in the V1/V2 Telegram dispatch for weeks.

### Cycle-2-Backlog (Polish, non-blocking)

1. **CWD hint** for subagent use-cases: "when your CWD is not the target repo: first `cd` or delegate commands to user". GREEN subagent had a CWD mismatch (vault instead of repo) and had to solve that via command suggestions.
2. **LSP find_references as complement source** (not only as anti-pattern): for LSP-capable repos additional verification alongside grep.
3. **Schema-use-case mismatch as explicit sub-check** in Step 3: for DB-backed lookups (`instruments.display_name IS NULL`) a DB-data-state check before migration is needed — own drift class.
4. **High-risk paths list** for the codebase as Quick Reference: notification/, scheduler/, briefings/, analytics/, tests/integration/ — project-specifically valuable.
