---
name: asyncio-fire-and-forget-loop-exit-await
description: Use when writing or reviewing Python code that uses `asyncio.run(...)` as entry-point AND inside the entry-coroutine uses `asyncio.create_task(...)` for fire-and-forget background work (notifications, telemetry, advisor-calls, fan-out HTTP/DB-writes). Without an explicit `await asyncio.gather(*pending_tasks)` before the entry-coroutine returns, `asyncio.run()` closes the event-loop and CANCELS any still-pending tasks → silent data-loss (0-50% of background work lost depending on task duration vs main-coroutine duration). Trigger on phrases like "asyncio.run + create_task", "fire-and-forget cancelled at loop-exit", "background tasks not running", "telemetry/notification silent dropping", "advisor calls cancelled", "pending tasks cancelled at shutdown", "asyncio task silently lost", "Loop closed before task finished". Do NOT load for asyncio.Runner / asyncio.gather-as-entry patterns (loop stays open until gather completes — no fire-and-forget issue), for long-running daemons (uvicorn/asyncio.Event.wait — loop never exits in normal-path), for sync code with threading.Thread (different cancellation model), or for non-Python async (JS/Go have different semantics). Technology-specific: Python 3.8+ asyncio. This skill encodes a code-review finding: a Per-Signal-Advisor in an orchestrator was fire-and-forget-dispatched via `asyncio.create_task(advisor_consult(signal))` after sending an alert; the orchestrator did sequential per-symbol-processing and returned. Code-Review caught it pre-deploy — without the fix, 0-50% of Advisor-calls would have been silently cancelled because the Claude API takes 5-30s and the orchestrator's remaining work takes <2s.
---

# asyncio fire-and-forget loop-exit-await pattern

## The Iron Law

If you use `asyncio.run(main())` as entry-point AND `asyncio.create_task(...)` for background work inside `main()`, **`main()` MUST await all pending tasks before returning** — otherwise `asyncio.run()` closes the loop and silently cancels them.

## When the Bug Bites

The bug is **silent and partial**:
- Tasks that complete BEFORE `main()` returns → fine
- Tasks still pending when `main()` returns → cancelled, no error, no log (unless you handle CancelledError)

Typical victim pattern: `main()` does N iterations, each iteration dispatches a quick fire-and-forget task. The Nth iteration's task starts a 10s Claude-API-call, then `main()` returns immediately → that last task is killed mid-flight. Earlier tasks may also be partially incomplete.

In the real-world case: a Per-Signal-Advisor calling the Claude API (5-30s) was dispatched after each signal in an orchestrator loop that completed in ~2-5s. Estimated 0-50% silent task-cancellation depending on signal-count and API-latency.

## The 3-Step Fix

```python
async def main():
    tasks: list[asyncio.Task] = []
    
    for item in items:
        # ... existing work ...
        # Step 1: TRACK the task in a local list (not just create_task and forget)
        tasks.append(asyncio.create_task(background_work(item)))
    
    # Step 2: Before returning, await ALL pending tasks with a sensible timeout
    if tasks:
        n_pending = sum(1 for t in tasks if not t.done())
        if n_pending:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=60.0,  # tune to your slowest expected task
                )
                # Step 3: Inspect results, log errors, NEVER re-raise
                n_errors = sum(1 for r in results if isinstance(r, BaseException))
                if n_errors:
                    logging.warning("%d/%d background tasks raised", n_errors, len(tasks))
            except asyncio.TimeoutError:
                n_still_pending = sum(1 for t in tasks if not t.done())
                logging.warning("%d tasks exceeded %ds — cancelled", n_still_pending, 60)
    
    return 0  # NOW it's safe to return; asyncio.run() can close loop cleanly

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

**Why `return_exceptions=True`**: without it, the first exception in any task cancels all sibling tasks and propagates up — usually NOT what fire-and-forget callers want. With it, every task either completes-result or completes-exception, and you log/count without surprise re-raises.

**Why a timeout**: protects against one hung task blocking shutdown indefinitely. Pick a value greater than your slowest expected background-call (Claude API: 30s sane upper bound, so use 60s).

## Detection Checklist (for code-review)

When reviewing a Python file with `asyncio.run(...)` as entry-point:

1. Grep for `asyncio.create_task` inside the entry-coroutine or its callees.
2. For each `create_task`: trace whether the task-handle is awaited before the outermost coroutine returns. If the handle is discarded (anonymous expression) → 🔴 Critical.
3. Check: is the dispatched coroutine longer-running than the dispatcher? (Common offender: API-calls, DB-writes-with-network, slow file-IO.) If yes → 🔴 Critical for silent data-loss.
4. Check: is there an existing `asyncio.gather(...)` or similar at the bottom of the entry-coroutine that catches pending tasks? If yes → ✓.

## Anti-Patterns

- ❌ `asyncio.create_task(f())` with no name, no list, no await — pure fire-and-forget. Bug-guaranteed in `asyncio.run()` contexts.
- ❌ Trying to await INSIDE the loop (`await asyncio.create_task(...)`) — that defeats the parallelism purpose.
- ❌ Using `asyncio.ensure_future` instead of `create_task` — same problem, slightly less obvious.
- ❌ Catching `CancelledError` inside the background-coroutine and treating it as "normal" — masks the bug, doesn't fix it.
- ❌ "Add a `time.sleep(5)` at end of main to give tasks time" — fragile, doesn't scale, looks bad in code-review.

## When You Don't Need This

- **Long-running daemons** (FastAPI/Uvicorn, asyncio-based servers, `asyncio.Event().wait()` loops): the loop runs until externally stopped — pending tasks have time to complete, or you have explicit shutdown-hooks. No bug.
- **Coroutines using `asyncio.gather` as their main fan-out**: `gather()` itself awaits, so no orphan tasks.
- **Sync-only code**: no event-loop, no issue.

## Related

- Python docs: [asyncio.run](https://docs.python.org/3/library/asyncio-runner.html#asyncio.run) — note the "Closes the loop and finalizes asynchronous generators" line, which is exactly what cancels pending tasks.
- Sibling skill: `code-review-chunk-dispatch` (for catching this class of bug via subagent-review).
- The maxim "Code-Review as standard": this bug was caught Day 2 in a row by the subagent-review pattern.

## Edge-Cases & Aggravators

- **Sync-IO in async context**: if the symbol loop makes blocking calls (yfinance without await, blocking psycopg2 cursor), it blocks the event loop and prevents parallel Advisor-tasks from making progress — the silent-cancel rate rises. Check during review: are all IO calls async? Otherwise the bug escalates further.
- **Extended-Thinking-Timeouts**: the default `timeout=60s` is sized for Claude Sonnet without Extended-Thinking. With `thinking_enabled=True` and a high token budget, calls can take 60-180s — raise the timeout or rethink the pattern architecture (background worker instead of fire-and-forget).
- **uvicorn reload mode**: in dev with `--reload`, uvicorn periodically restarts — pending tasks are cancelled on each reload. In prod (no reload) this is not the problem, but dev tests can mask the bug if they straddle a reload cycle.

## Background: Real-World Case

A Per-Signal-Advisor in `scripts/v3_orchestrator.py` of your-app:
- `_orchestrate(args)` loops over symbols, each iteration: scan_signal + persist + send_telegram + `asyncio.create_task(advisor_consult(signal))`
- After the loop: stage-monitor + PnL-update (~2s) → `return 0`
- `asyncio.run(_orchestrate(args))` closes the loop → all create_task'd Advisor-calls cancelled
- Advisor-calls take 5-30s (Claude Sonnet API)
- Silent data-loss estimated 0-50% of Advisor verdicts (depending on signal-count and order)

Fix: tasks tracked in `advisor_tasks: list[asyncio.Task]`, `await asyncio.wait_for(asyncio.gather(*advisor_tasks, return_exceptions=True), timeout=60.0)` before `return 0`. Caught by code-review subagent in a Spec→Plan→Implementation→Review cycle before any deploy.

## Background: TDD Log (Bulletproofing)

### Cycle 1 — PASS via Subagent-Pair-Dispatch (Tempo-Booster class)

- **RED subagent** (without skill, prompt: review a v3_orchestrator snippet with `create_task(advisor_consult)` + asyncio.run): **found the critical bug on its own**! Wrote a precise fix with `await asyncio.gather(*advisor_tasks, return_exceptions=True)` — nearly identical to the skill's 3-step fix. RED was surprisingly smart; the skill here is not a "bug preventer" but a "tempo booster + consistency guarantee".

- **GREEN subagent** (with skill, identical prompt): structured output, impact quote 0-50% explicitly computed, `wait_for + timeout` added, `return_exceptions=True` rationale clean. Additionally discovered an important issue "sync-IO in async context as an aggravator" — RED without the skill would not have included that in the review.

- **Refactor applied**: section "Edge-Cases & Aggravators" added (sync-IO, Extended-Thinking-Timeouts, uvicorn reload mode) — from GREEN self-reflection. Improves the depth of the detection checklist.

### Polish-vs-Promote verdict

Comparable to `pytest-venv-first-triage`: smart-RED finds the bug, the skill provides tempo + consistency + avoidance of alternative anti-patterns (`time.sleep`, `ensure_future`, `CancelledError`-catch). Promote argument: in reviews with cognitive load (multi-bug file) consistency is more valuable than per-bug hit rate.

### Cycle-2 Backlog (Polish, non-blocking)

1. **AnyIO variant**: same pattern for `anyio.run(...)` + `anyio.create_task_group()` — anyio enforces structured concurrency but pattern drift in codebases is possible
2. **TaskGroup PEP-654**: Python 3.11+ `asyncio.TaskGroup` as the idiomatic replacement for manual `gather` — once widely adopted, add a dedicated "Modern Alternative" section
3. **Telemetry integration**: logging hook for the `n_errors`/`n_pending` counters into a central telemetry system (instead of only log.warning) — application-specific
