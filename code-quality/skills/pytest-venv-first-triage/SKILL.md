---
name: pytest-venv-first-triage
description: Use when pytest shows multiple failures or errors (especially ModuleNotFoundError clusters) and you're about to dig into individual test fixes. ALWAYS check the Python environment FIRST — `which python3` vs `venv/bin/python3` — before debugging individual tests. System-Python frequently lacks project deps (cachetools, asyncpg, etc.) while project venv has them. Trigger on phrases like "pytest shows many failures", "test errors after pull", "these tests were green yesterday", "ModuleNotFoundError multiple files", "pre-existing failures", "tests broken without code change", "ImportError test sweep". Do NOT load for single-test-fail debugging (use systematic-debugging directly), for Python projects without venv (no env mismatch possible), or for failures with clear test-logic bugs (e.g. assertion errors with concrete values).
---

# pytest venv-first Triage

> ✅ **PROMOTED**: TDD pressure-test passed with interesting variability. RED-Subagent itself recognized the env-mismatch pattern (smart-RED) and recommended env-check before code-debug — but with a longer reasoning tour. GREEN-Subagent delivered identical diagnosis in <60s via Quick-Check-Procedure block + pattern-match confidence from skill data. Skill is valuable as a tempo booster + insurance against less-smart subagents. Cycle-2 backlog: direnv/pyenv/poetry/uv mention, pre-commit hook hint, Makefile `make test` pattern.

## Pattern (short form)

**Before every pytest failure debug dive**: check whether you're using the right Python environment.

```bash
# 1. Which python3 points to which environment?
which python3
python3 -c "import sys; print(sys.prefix)"

# 2. Is there a project venv?
ls -d venv 2>/dev/null && ls venv/bin/python*

# 3. If yes: re-run with venv python
venv/bin/python3 -m pytest <same args> -q
```

If (3) delivers drastically different failure counts → 90% of the "pre-existing failures" were environment mismatch, not code bug.

## Symptoms (how to tell it's the venv)

- **ModuleNotFoundError cluster** in a subdirectory (e.g. all tests in `tests/test_dashboard/` failed → probably import error in a shared file of that subdir)
- **"These tests were green"** — nothing in the code was changed, but pytest shows 30+ failures
- **`sys.prefix` shows `/Library/Frameworks/Python.framework/...`** instead of `/path/to/project/venv`
- **`which python3`** shows `/usr/local/bin/python3` or `/usr/bin/python3` instead of `venv/bin/python3`
- pre-commit hook ran successfully but local full-suite run failed (hook maybe uses system python, locally should be venv)

## Concrete example

Full-suite run: 1894 passed, **15 failed, 32 errors**. Triage suspicion: pre-existing failures. Detailed look at first error:

```
ERROR tests/test_dashboard/test_cockpit_page.py::test_status_page_returns_200
    from cachetools import TTLCache
E   ModuleNotFoundError: No module named 'cachetools'
```

Check:
```bash
$ grep -i cachetools requirements.txt
cachetools>=5.3  # in requirements ✓

$ which python3
/usr/local/bin/python3                              # ← system python

$ python3 -c "import sys; print(sys.prefix)"
/Library/Frameworks/Python.framework/Versions/3.14  # ← Apple Python.framework

$ ls venv/bin/python*
venv/bin/python3                                    # ← venv exists

$ venv/bin/python3 -c "import cachetools; print(cachetools.__version__)"
cachetools OK: 7.1.1                                # ← venv has it
```

Re-run with venv python: **1946 passed, 1 failed** (real test bug, quickly fixed). 47 of 48 failures were env mismatch.

## Diagnosis table

| Symptom | Cause | Action |
|---|---|---|
| `which python3` = system path + venv dir exists | venv not activated | `venv/bin/python3 -m pytest ...` or `source venv/bin/activate` |
| ModuleNotFoundError for modules from requirements.txt | venv installed all deps, system python didn't | use venv |
| pre-commit OK, local failed | hook + local use different pythons | normalize both to venv |
| CI green, local failed | CI uses requirements-installed container, local system python | use venv |
| Failures in a subdir cluster | shared import in subdir crashes all tests | after env check, check code diff |
| Failures scattered + without module pattern | real code bug | normal debug workflow |

## When NOT to use (real code-bug indicators)

- Failures spread over many subdirs WITHOUT a common import module
- AssertionError with concrete expected-vs-actual values
- Failure count doesn't change between system python and venv python
- Failures started only after a concrete commit sweep (file-path-diff then helpful)

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| Jump immediately into test-by-test debug because "32 failures are real" | FIRST env check (30 seconds), THEN debug |
| `pip install <missing-module>` into system python instead of venv switch | In venv you land in requirements.txt consistency; system-pip-install collides with brew/Apple-Python updates |
| Assume pre-commit hook uses venv (maybe it doesn't) | Check pre-commit config explicitly: `cat .pre-commit-config.yaml \| grep python` |
| Mark failures as "pre-existing acceptable" without env check | You may be the only person running these tests — no one saw the failures before |
| 30+ minutes spent in code-diff triage without env check | Env check is 30s, file-path-diff can still follow after env check |

## Quick-Check Procedure (60 seconds)

```bash
# Diagnosis block — copy-paste-ready
echo "=== Active Python ==="; which python3
echo "=== sys.prefix ==="; python3 -c "import sys; print(sys.prefix)"
echo "=== venv exists? ==="; ls -d venv 2>/dev/null && echo "YES" || echo "NO"
[ -x venv/bin/python3 ] && echo "=== venv python ==="; venv/bin/python3 -c "import sys; print(sys.prefix)"
echo "=== requirements check ==="
[ -f requirements.txt ] && head -10 requirements.txt

# If system python is active + venv exists → re-run:
venv/bin/python3 -m pytest <previous args> -q 2>&1 | tail -5
```

## TDD task for next skill-building session

1. **RED**: subagent without skill gets pytest output with 32 ModuleNotFoundError errors. Observe: does it dive directly into code-debug or first ask env? Likely: code-debug.
2. **GREEN**: with skill: same task. Should FIRST run env-check + Quick-Check Procedure.
3. **REFACTOR**: loophole "but requirements.txt contains cachetools, so pytest is certainly green in venv" → skill must make explicit that requirements ≠ activated venv.
4. **Trigger phrases**: "pytest many failures", "tests broken without code change", "ModuleNotFoundError multiple" → does the skill get auto-triggered?

## Cross-references

- `superpowers:systematic-debugging` — overarching debug framework, this skill is special case "first check env"
- `your-server-fastapi-iteration` — repo-specific Python setup conventions

## Real-world impact

Initial run with system python:
- 1894 passed, 15 failed, 32 errors (47 apparent pre-existing failures)
- Triage suspicion: jumping into code debug would cost ~1-2h

With venv-python re-run:
- 1946 passed, 1 failed (real bug, 5min fix)
- Real saving: ~30-60 min avoided, plus confidence gained that nothing substantial was actually broken

If this skill had been available: 60s env check immediately, 5min real-bug fix, done.

## Background: TDD progression (Bulletproofing-Log)

### Cycle 1 — PASS — with variability note

- **RED-Subagent** (without skill, 47-failures diagnosis task): remarkably smart — itself recognized that `requirements.txt` contains cachetools but import fails → env-mismatch hypothesis. Suggested env-check before code-debug. Counter-thesis check made explicit ("could the 15 failures be real code bugs? — don't know yet, first fix env"). Very close to GREEN behavior.
- **GREEN-Subagent** (with skill, same prompt): identical diagnosis logic, but more structured (Quick-Check Procedure block from skill taken 1:1) + higher confidence through pattern-match with documented real case (same paths, same module, same cluster). Verification steps more precise.
- **Verdict**: GREEN not superior over *this* RED — but RED-subagent variability is real (some subagents would jump directly into code-debug). Skill remains valuable as tempo booster + insurance.

### Cycle-2-Backlog (Polish, non-blocking)

1. **direnv / pyenv / poetry / uv** as alternative venv indirections to mention (`which python3` can mislead)
2. **pre-commit hook consistency tip**: after venv switch, `pre-commit run --all-files` should deliver the same output
3. **Defensive measures after fix**: `.envrc` snippet or `Makefile` target `make test` for permanent avoidance
4. **Fallback without venv dir** (test scenario today): "if no venv: first `python3 -m venv venv && pip install -r requirements.txt` before attempting the re-run" as a more robust branch
