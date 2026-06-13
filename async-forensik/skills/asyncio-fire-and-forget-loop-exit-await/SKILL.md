---
name: asyncio-fire-and-forget-loop-exit-await
description: Use when writing or reviewing Python code that uses `asyncio.run(...)` as entry-point AND inside the entry-coroutine uses `asyncio.create_task(...)` for fire-and-forget background work (notifications, telemetry, advisor-calls, fan-out HTTP/DB-writes). Without an explicit `await asyncio.gather(*pending_tasks)` before the entry-coroutine returns, `asyncio.run()` closes the event-loop and CANCELS any still-pending tasks → silent data-loss (0-50% of background work lost depending on task duration vs main-coroutine duration). Trigger on phrases like "asyncio.run + create_task", "fire-and-forget cancelled at loop-exit", "background tasks not running", "telemetry/notification silent dropping", "Advisor-Calls werden cancelled", "pending tasks cancelled at shutdown", "asyncio task silently lost", "Loop closed before task finished". Do NOT load for asyncio.Runner / asyncio.gather-as-entry patterns (loop stays open until gather completes — no fire-and-forget issue), for long-running daemons (uvicorn/asyncio.Event.wait — loop never exits in normal-path), for sync code with threading.Thread (different cancellation model), or for non-Python async (JS/Go have different semantics). Technology-specific: Python 3.8+ asyncio. This skill encodes a 27.05.2026 Wolf-Code-Review finding: a Per-Signal-Advisor in `scripts/v3_orchestrator.py` was fire-and-forget-dispatched via `asyncio.create_task(advisor_consult(signal))` after `send_signal_alert`; the orchestrator did sequential per-symbol-processing and returned. Code-Review caught it pre-deploy — without the fix, 0-50% of Advisor-calls would have been silently cancelled because Claude-API takes 5-30s and the orchestrator's remaining work (stage-monitor + PnL-update) takes <2s.
---

# asyncio fire-and-forget loop-exit-await pattern

## The Iron Law

If you use `asyncio.run(main())` as entry-point AND `asyncio.create_task(...)` for background work inside `main()`, **`main()` MUST await all pending tasks before returning** — otherwise `asyncio.run()` closes the loop and silently cancels them.

## When the Bug Bites

The bug is **silent and partial**:
- Tasks that complete BEFORE `main()` returns → fine
- Tasks still pending when `main()` returns → cancelled, no error, no log (unless you handle CancelledError)

Typical victim pattern: `main()` does N iterations, each iteration dispatches a quick fire-and-forget task. The Nth iteration's task starts a 10s Claude-API-call, then `main()` returns immediately → that last task is killed mid-flight. Earlier tasks may also be partially incomplete.

In Wolf's 27.05.2026 case: a Per-Signal-Advisor calling Claude API (5-30s) was dispatched after each v3-signal in an orchestrator loop that completed in ~2-5s. Estimated 0-50% silent task-cancellation depending on signal-count and API-latency.

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
- Wolf-Maxime „Code-Review als Standard" (CLAUDE.md): this bug was caught Day 2 in a row by the subagent-review pattern.

## Edge-Cases & Verschärfer

- **Sync-IO im async-Context**: wenn die Symbol-Loop blocking-Calls macht (yfinance ohne await, blocking psycopg2-Cursor), blockiert das den Event-Loop und verhindert dass parallele Advisor-Tasks Fortschritt machen — die silent-cancel-Quote steigt. Check beim Review: alle IO-Calls async? Sonst eskaliert der Bug zusätzlich.
- **Extended-Thinking-Timeouts**: das Default-`timeout=60s` ist für Claude Sonnet ohne Extended-Thinking-Modus dimensioniert. Bei `thinking_enabled=True` mit hohem token-budget können Calls 60-180s gehen — Timeout-Wert hochziehen oder Pattern-Architektur überdenken (Background-Worker statt fire-and-forget).
- **uvicorn-Reload-Modus**: in Dev mit `--reload` startet uvicorn periodisch neu — pending tasks werden bei jedem Reload gecancelt. In Prod (kein Reload) ist das nicht das Problem, aber Dev-Tests können den Bug maskieren wenn sie über einen Reload-Cycle hinweg laufen.

## Background: 27.05.2026 Real-World-Case

Per-Signal-Advisor in `scripts/v3_orchestrator.py` of ultimative-platform:
- `_orchestrate(args)` loops over symbols, each iteration: scan_signal + persist + send_telegram + `asyncio.create_task(advisor_consult(signal))`
- After loop: stage-monitor + PnL-update (~2s) → `return 0`
- `asyncio.run(_orchestrate(args))` closes loop → all create_task'd Advisor-Calls cancelled
- Advisor-Calls take 5-30s (Claude Sonnet API)
- Silent data-loss estimated 0-50% of Advisor-verdicts (depending on signal-count and order)

Fix: tasks tracked in `advisor_tasks: list[asyncio.Task]`, `await asyncio.wait_for(asyncio.gather(*advisor_tasks, return_exceptions=True), timeout=60.0)` before `return 0`. Caught by code-review-subagent in Spec→Plan→Implementation→Review-cycle before any deploy. Commit `ee26365`.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS via Subagent-Pair-Dispatch, Tempo-Booster-Class)

- **RED-Subagent** (ohne Skill, Prompt: Review eines v3_orchestrator-Snippets mit `create_task(advisor_consult)` + asyncio.run): **fand den Critical-Bug eigenständig**! Schrieb präzisen Fix mit `await asyncio.gather(*advisor_tasks, return_exceptions=True)` — fast identisch zum Skill-3-Step-Fix. RED war überraschend smart, Skill ist hier nicht „Bug-Verhinderer" sondern „Tempo-Booster + Konsistenz-Garantie".

- **GREEN-Subagent** (mit Skill, identisches Prompt): strukturierter Output, Impact-Quote 0-50% explizit berechnet, `wait_for + timeout` zusätzlich, `return_exceptions=True`-Begründung sauber. Zusätzlich Important-Issue „sync-IO im async-Context als Verschärfer" entdeckt — das hätte RED ohne Skill nicht in Review aufgenommen.

- **Refactor angewendet**: Sektion „Edge-Cases & Verschärfer" hinzugefügt (sync-IO, Extended-Thinking-Timeouts, uvicorn-Reload-Modus) — aus GREEN-Self-Reflection. Verbessert die Detection-Checklist-Tiefe.

### Polish-vs-Promote-Verdict

Vergleichbar mit `pytest-venv-first-triage` aus 27.05.-Promotion-Session: smart-RED erkennt den Bug, Skill bringt Tempo + Konsistenz + Vermeidung von Alternative-Anti-Patterns (`time.sleep`, `ensure_future`, `CancelledError`-catch). Promote-Argument: bei Reviews mit kognitiver Last (multi-bug-File) ist Konsistenz wertvoller als Hit-Rate auf einzelne Bugs.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **AnyIO-Variant**: dasselbe Pattern für `anyio.run(...)` + `anyio.create_task_group()` — anyio macht structured concurrency aber Pattern-Drift in Codebases ist möglich
2. **TaskGroup-PEP-654**: Python 3.11+ `asyncio.TaskGroup` als idiomatischer Ersatz für manuelles `gather` — wenn breit verbreitet, eigene Sektion „Modern Alternative"
3. **Telemetry-Integration**: Logging-Hook für die `n_errors`/`n_pending`-Counters in ein zentrales Trading-Telemetry-System (statt nur log.warning) — projekt-spezifisch für ultimative-platform
