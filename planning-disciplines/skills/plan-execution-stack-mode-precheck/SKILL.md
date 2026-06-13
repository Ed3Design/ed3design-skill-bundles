---
name: plan-execution-stack-mode-precheck
description: Use as Pre-Step-0 of `executing-plans` / `subagent-driven-development` / inline-plan-execution when the plan contains `docker compose exec`, SSH commands or other stack-interaction steps. The check distinguishes (a) local-runnable-stack vs (b) remote-only-stack vs (c) hybrid-mode (code-local + live-remote). Prevents mid-execution stop-gates when the plan implicitly assumes "docker compose works here" but secrets/.env.prod, env-files, or services are missing locally. Trigger on phrases like "execute the plan", "executing the plan", "subagent-driven execution start", "docker compose exec in plan steps", "deploy stack vs dev stack", "your-server vs local" mid-plan. Do NOT load for plans without stack interaction (pure-function-only-tasks), for plans where stack-mode is explicitly documented, or for the initial plan-writing phase (writing-plans has its own self-review).
---

# plan-execution-stack-mode-precheck (DRAFT — TDD-Promotion-Pending)

> ⚠️ **DRAFT**: Pattern from a Phase-Z.1 execution session. The Z.1 plan had `docker compose exec` steps that implicitly assumed "local stack running". Locally `secrets/.env.prod` was missing AND the Docker daemon was off → a 2-step stop-gate mid-execution cost ~20 min of session time + mode pivot to hybrid. Would have been prevented by a 5-minute pre-check before Z.1 start.

## Lifecycle position

Pre-step for any plan-execution workflow:

```
[Plan exists] → writing-plans Self-Review ✓
              ↓
[Execution starting] → THIS Skill (Pre-Step-0 Stack-Mode-Check)
              ↓
[Mode clear] → executing-plans / subagent-driven-development / inline
```

## The three stack modes

| Mode | Description | Plan-step effect |
|---|---|---|
| **Local-Runnable** | Compose file + all env files + services runnable locally | run all `docker compose exec` as-is |
| **Remote-Only** | Stack runs ONLY on server (your-server / cloud) | run all `docker compose exec` via SSH OR deferred |
| **Hybrid** | Code locally developable, live-verify only remote | code steps local, live-verify steps marked as "pending remote-deploy" |

## Pattern (4 steps)

### Step 1: Compose-file inspect (10 sec)

```bash
# Find docker-compose.yml / compose.yml
find . -maxdepth 3 -name "compose.yml" -o -name "docker-compose.yml" 2>/dev/null | head -3

# Inspect env-file requirements
grep -E "env_file|secrets|env_var" $(find . -maxdepth 3 -name "compose.yml" -o -name "docker-compose.yml" | head -1)
```

Output shows which `.env` / secrets files the compose setup expects.

### Step 2: Env-files existence check (5 sec)

```bash
# For each env file referenced by compose
for f in .env .env.prod secrets/.env.prod docker/.env; do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ $f MISSING"
done
```

If a MUST-EXIST file is missing → mode is NOT "Local-Runnable" for this stack operation.

### Step 3: Daemon + services sanity (15 sec)

```bash
# Docker daemon up?
docker info >/dev/null 2>&1 && echo "✓ daemon up" || echo "✗ daemon down (open -a Docker on Mac)"

# Services running?
docker compose -f <compose-file> ps 2>&1 | head -5
```

If daemon down OR `ps` returns empty → stack is not ready. Plan steps that need `exec` will fail.

### Step 4: Mode verdict + plan annotation

Based on Steps 1-3:

- **Local-Runnable**: continue with plan as-is. Optionally start stack (`docker compose up -d`).
- **Remote-Only**: check plan step by plan step — what MUST run locally (code edit, pytest mock tests), what MUST be remote (DB migration live, live backfill, live backtest)?
- **Hybrid**: explicit split documented in daily note:
  - Local today: all code tasks + pure-function tests + mock-integration tests
  - Remote tomorrow: live DB migration, live backfill, live backtest, 24h-cycle verify

## Annotation pattern for plan steps

For each `docker compose exec` line in the plan:

```markdown
- [ ] **Step N: <Action>**

Run:
```bash
docker compose exec app python -m scripts.X
```
**Stack-Mode**: LOCAL-ONLY / REMOTE-ONLY / HYBRID-pending-remote
```

In hybrid mode: all REMOTE-pending steps in daily-note carry-over block, NOT marked as "DONE" before remote execution.

## 24h-cycle-before-closed-as-done — maxim application

Maxim: "Code-complete ≠ Task-DONE until 24h live cycle confirms the success criterion."

In hybrid mode this becomes mechanically important:
- Local tests green ≠ Task-DONE
- DONE marker only AFTER successful server live run + 24h-cycle verify

In roadmap: explicit separation "Code-Complete" vs "Live-Verified".

## Anti-patterns

| Anti-pattern | Correct |
|---|---|
| Start `executing-plans` directly without stack-mode check | Pre-Step-0 at 30sec total takes less than 5-10min mid-execution stop |
| Stack-mode pivot in middle of subagent-driven loop | Pivot COSTS subagent overhead — clarify before first subagent dispatch |
| "DONE" marker for code-complete-but-not-live-verified | Maxim: 24h cycle before closed-as-done. Hybrid = "Code-Complete, pending Live-Verify" |
| Plan writing without stack-mode annotation | writing-plans self-review should check that (memory item for plan author) |
| Docker.app start mid-execution | Pre-Step-0 starts daemon parallel to compose inspect (10sec parallel save) |

## Cross-references

- `superpowers:executing-plans` — parent workflow (this skill is Pre-Step-0)
- `superpowers:subagent-driven-development` — parent workflow (same)
- `superpowers:writing-plans` — plan writing should contain stack-mode annotation (cycle-2 backlog for writing-plans skill)
- `your-server-fastapi-iteration` — if stack mode = remote-only, this skill for live deploy
- `tailscale-multi-account-diagnosis` — if remote connection broken

## Real-world impact

- **Z.1 execution start** without pre-check → Docker daemon down (10sec stop) + `secrets/.env.prod` missing (15min mode pivot)
- **Would have been caught with pre-check** in 30sec → hybrid-mode decision BEFORE first code edit
- **Token cost**: ~30k mid-execution recovery due to mode pivot — saved by Pre-Step-0
- **Structural lesson**: Plan Z.1 itself was not "wrong", but the `docker compose exec` steps needed explicit stack-mode annotation. → Memory item for `writing-plans` sub-step.

## TDD task for future promotion

Before GA promotion of this skill:

1. **RED scenario**: User says "start execution of plan X" (plan contains `docker compose exec`, stack is remote-only) — RED without skill probably starts plan step 1, fails at docker command
2. **GREEN scenario**: same prompt, with THIS skill — GREEN does Pre-Step-0 stack-mode check, identifies remote-only, proposes hybrid mode
3. **Expected RED failure mode**: 5-10min mid-execution discovery vs GREEN's 30sec pre-check
4. **Verdict criterion**: GREEN presents mode verdict + plan annotation BEFORE code action

## Background: TDD log (Bulletproofing-Log)

### Cycle 1 (DRAFT phase)

Skeleton from a Phase-Z.1 execution session. Real TDD pressure test pending. Pattern ad-hoc applied (after the stop-gate appeared):
- Docker.app start parallelized with working-tree cleanup
- `secrets/.env.prod` existence check revealed remote-only stack reality
- Hybrid-mode decision via AskUserQuestion (user chose "continue through" → hybrid)
- Plan steps split into "local today" vs "server tomorrow" in daily-note block 5

Result: Phase Z.1 9-tasks code-complete despite stack-mode mismatch — through ad-hoc hybrid instead of plan mid-stop. Skill existence would have saved the pivot detour.
