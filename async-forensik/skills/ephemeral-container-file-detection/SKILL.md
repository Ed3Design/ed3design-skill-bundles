---
name: ephemeral-container-file-detection
description: |-
  Use when designing or auditing Docker-based deployments BEFORE writing implementation plans that rely on files persisting across container rebuilds. Trigger on phrases like "volume mount for X", "why are the files gone", "container rebuild deleted my models", "model_path points to a file that's not there", "phantom registry in DB", "inference fails with FileNotFoundError", "before we build — are the prerequisites in place", "pre-flight deployment audit", "writing-plans for a Docker feature with persistent data". Detection-Pattern in 4 steps: docker inspect Mounts → ls container dir → stat birth-time → grep dump/save calls in code → if code writes but the mount list does NOT include the path → ephemeral, pre-flight STOP for the feature phase. Do NOT load for non-Docker deployments (systemd services, Kubernetes StatefulSets — different model), for read-only containers without write paths, for single-file apps without a storage layer. The maxim "read logs/code/DB first" applied to deployment prerequisites.
---

# ephemeral-container-file-detection

> ✅ **PROMOTED** 2026-06-15 — TDD pressure-test PASS. RED-Subagent wrote naive 2-task plan with `joblib.dump` to an unmounted path and `Path.exists()` verify-step that would pass once then silently break on next `up --build`. Honesty-section: "I treated the filesystem as persistent because the scenario described `joblib.dump` + `joblib.load` as if it worked". GREEN-Subagent applied 4-step check, identified 🚨 EPHEMERAL row, proposed Phase W (volume mount + DB reconciliation) BEFORE writing the original plan. Cycle-2 polish items in TDD-Verlauf log below.

## Pattern (short form)

Before every implementation plan for a Docker-based feature that **requires persistent state** (ML models, caches, upload files, user data, trained embeddings, etc.):

### 4-step check

1. **Docker inspect mounts**:
   ```bash
   docker inspect <container_name> | grep -A 3 -E 'Mounts|Source|Destination'
   ```
   Lists all bind mounts + named volumes.

2. **Container dir reality**:
   ```bash
   docker exec <container_name> ls -la <expected_path>/
   ```
   What is *actually* in that directory inside the running container?

3. **Stat birth time of the container directory**:
   ```bash
   docker exec <container_name> stat <expected_path>/
   ```
   `Birth:` shows when the directory was created inside the container. If birth ≈ last container build time → ephemeral image layer (not persistent).

4. **Code grep for save calls**:
   ```bash
   grep -rn "joblib.dump\|to_csv\|save_model\|pickle.dump\|open.*'w'\|aiofiles.open" --include="*.py" <code_root> | grep -i <expected_path-substring>
   ```
   Finds places where code writes to the expected path.

### Diagnosis table

| Step 1 (Mount?) | Step 4 (Code writes?) | Verdict |
|---|---|---|
| ✅ Mount exists | ✅ Code writes | OK — persistent storage works |
| ❌ No mount | ❌ Code doesn't write | OK — only read-only container-layer files |
| ❌ No mount | ✅ Code writes | 🚨 **EPHEMERAL** — files vanish on every `up --build` |
| ✅ Mount exists | ❌ Code doesn't write | OK but: mount may be obsolete (cleanup candidate) |

The 🚨 pattern is the **pre-flight stop trigger** for the feature phase.

## Concrete example (live encounter)

**Task**: write an implementation plan for your-app Phase X.0 (ML evaluator).

**Pre-flight discovery**:
- Step 1: `docker inspect your-trader-app | grep Mounts` → only `<host-data-dir>/your-app/logs:/app/logs`, NO `/app/ml/models` mount
- Step 2: `docker exec your-trader-app ls /app/ml/models/` → only `model_TEST_DE.pkl` + `.gitkeep` (1 file out of 40 expected)
- Step 3: `stat /app/ml/models/` → Birth: 14:13:35 UTC (yesterday's container rebuild for the Phase-2e deploy)
- Step 4: `grep -rn "joblib.dump" --include="*.py" ml/` → `ml/ranking_model.py:153: joblib.dump(self, path)`

**Diagnosis**: code writes to `/app/ml/models/`, but the path is NOT mounted → **ephemeral**. 40 `ml_models` DB entries are a phantom registry since the last rebuild.

**Consequence**: the Phase-X.0 plan was NOT written. Instead, Phase W was inserted as a pre-phase (volume mount + retraining + verify). ~4-6h of wasted plan-work prevented.

## Quick reference: when to run this check?

| Situation | Run check? |
|---|---|
| Implementation plan for Docker feature with `joblib.load`/`pickle.load`/`load_model` | ✅ YES, before writing the plan |
| Implementation plan for caching/upload/user-storage feature | ✅ YES, before writing the plan |
| User bug report "files are gone after deploy" / "inference fails with FileNotFoundError" | ✅ YES, as a diagnostic block |
| Database migration in container (DB data in volume) | ⚠ Usually OK because Postgres volumes are standard, but verify |
| Read-only container (e.g. stateless API) | ❌ No |
| systemd service deployment (no Docker) | ❌ No (different storage semantics) |
| Kubernetes StatefulSet | ⚠ Not this skill — Kubernetes PVC pattern is different |

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| Write the plan without pre-flight, then stop at task 0 | Run pre-flight BEFORE `writing-plans` |
| Ignore `docker inspect`, rely on reading compose.yml source | compose.yml and docker-inspect can diverge (the running container may be an old version) — check both |
| Accept ephemeral finding as "also okay" because "it's running right now" | Next rebuild wipes. Structural problem, not symptom |
| Only check container view, forget host view | With bind mount, also check `ls /host/path/` — bidirectional visibility is confirmation |
| Use `du -sh` to verify instead of file counts | `du` reports size, not count. Count is the relevant metric for "files persistent" |
| Pre-flight only for ML files, not for caches/sessions/uploads | The pattern applies to EVERY write-path pattern, not just ML |

## Pre-flight as a pre-step to superpowers:writing-plans

When this skill is activated for plan writing, the 4-step check belongs **as the very first task in the plan OR before plan writing**:

**Variant A — Pre-flight BEFORE plan writing** (recommended when prerequisites are unclear):
- Discovery first, plan then tailored to findings
- Used in the genesis case: Phase W inserted instead of planning Phase X.0 directly

**Variant B — Pre-flight as task 0 IN the plan** (when prerequisites are presumed-OK but to be verified):
- Plan contains an explicit "Task 0: pre-flight storage audit" with the 4 steps
- If task 0 fails → plan stop, redesign required
- Suitable for routine deployments with standard patterns

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-15 (PASS)

- **RED-Subagent** (without skill, ML-feature-plan-with-unmounted-models scenario): wrote routine 2-task plan with `joblib.dump` + `Path.exists()` verify-step. Honesty-section: "I defaulted to 'training pipeline + DB-insert + smoke-test'. I treated the filesystem as persistent because the scenario described `joblib.dump` + `joblib.load` as if it worked. I did NOT cross-reference the explicit mount-list against the write-path until the honesty-section forced me to."
- **GREEN-Subagent** (with skill, identical scenario): applied 4-step check, identified 🚨 EPHEMERAL diagnosis-row, proposed Phase W (verify ephemeral on live container + add bind-mount + reconcile DB-registry-vs-filesystem) as blocker BEFORE original plan. Self-reflection: "the canonical case the skill was extracted from" — exact trigger match.

### Cycle-2-Backlog (Polish, non-blocking)

1. **DB-reconciliation step needs to be explicit** in Phase W template (GREEN had to invent the `SELECT id, path FROM ml_models; for each row check os.path.exists(path)` reconcile pattern — not currently spelled out in the skill)
2. **Variant A/B decision-rule sharper**: if a phantom registry already exists in the DB → always Variant A (Pre-flight BEFORE plan writing), no judgment call
3. **Handling of stale rows** (retrain vs archive vs delete) is Wolf-decision-territory but should be flagged by the plan-writer, not solved silently

## Cross-references

- `superpowers:writing-plans` — the skill preaches "assume engineer has zero context", but pre-flight for storage prerequisites was not previously explicit
- `superpowers:brainstorming` — says "explore project context first" generally; this skill is the Docker-storage specialization
- maxim "read logs/code/DB first, then hypothesize" — extended to deployment prerequisites
- `timescaledb-compression-workflow` skill — related pattern: discovery-before-hypothesis in the storage area
- `pre-migration-data-verification` — related: verify data before adding a constraint; here verify storage before a feature plan

## Real-world impact

your-app Phase-X brainstorming session:
- **Spec** for Phase X.0 (ML evaluator) written with thresholds, filters, eval-report structure
- **Before plan writing**, pre-flight discovery executed (this pattern, informally)
- **Finding**: 40 ml_models DB entries point at `/app/ml/models/*.pkl`, in the container only `model_TEST_DE.pkl` (1 file), no volume mount → ephemeral
- **Consequence**: Phase W (volume mount + retraining + verify) as a new pre-phase, then Phase X.0
- **Time saved**: ~4-6h of plan writing + plan execution + plan abort prevented by early stop
- **Structural insight**: the G1 finding "v3 doesn't consume ml_models" had a deeper layer — even if v3 did consume, there would be nothing to consume (FileNotFoundError). Deployment-design bug, not concept gap

## Notes for skill reviewer (next session)

- If the skill passes TDD strongly: can become project-wide standard as a pre-step to `superpowers:writing-plans` for Docker features
- If TDD fails: extending the maxim "read logs/code/DB first" with storage verification may be enough — a separate skill would be overkill
- Variant to evaluate: does the pattern also apply to container-runtime state (in-memory caches, session stores)? Probably a different pattern (restart persistence vs. rebuild persistence)
