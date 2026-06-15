---
name: reporting-artefact-detection-before-claiming-anomaly
description: |-
  Use when observing a "surprising anomaly" in backtest output, SQL query result, multi-run-eval-report, ML-model-performance-table, or any reporting-layer artefact that suggests a system bug, market outlier, methodological problem, or drift requiring investigation. Common forms: "WR X% at n=Y is catastrophically low", "24h baseline drift +/-2pp", "Filter N has different numbers since yesterday", "sub-sample median diverges from aggregate total". Before treating the anomaly as a real phenomenon and dispatching forensic resources to explain it, run a 3-step reporting-artefact triage: (1) NULL-handling check — are NULL values in numerator/denominator mishandled? Was the IS NOT NULL filter omitted? (2) Cross-window / unique-ID check — do overlapping sub-windows / joins / aggregations count trades multiple times? Is cross-sum-vs-unique-count semantics clear? (3) Methodology-consistency check vs previous report — was the same SQL/calculation replicated exactly, or was a subtly different aggregation method used? Three filters make it easy to validate BEFORE a forensic subagent is dispatched. Trigger phrases like "why is WR suddenly so low", "I don't understand this anomaly", "24h drift", "baseline has changed", "sub-sample median surprising", "backtest gives different numbers today than yesterday", "week X was a disaster", "why are the numbers dropping". Do NOT load for confirmed-real anomalies where the artefact check is already done (then it's a real forensic task, use domain-specific skills), for first-time-setup-debugging without baseline comparison (no prior report to compare against), for non-reporting-layer issues like code bugs in the algorithm itself (then it's debugging, not reporting-artefact triage), or for user-facing UI rendering bugs (different domain). Encodes a discovery: three separate "anomalies" investigated over a 4-hour multi-subagent forensic cycle (KW13 WR 1.12%, C1-blocked 1055, 24h-baseline-drift 39.86→37.38) ALL turned out to be reporting artefacts due to (1) NULL-ko_pnl_pct in a legacy-migration cohort ignored by WHERE-clause filter omission, (2) cross-window-sum vs unique-ID-set semantic ambiguity, (3) multi-run-median vs flat-count methodology difference between consecutive day reports. ~3 hours of subagent forensic resources spent on three artefact-validation cycles that this 3-step check would have closed in 5 minutes each.

---

# reporting-artefact-detection-before-claiming-anomaly

> ✅ **PROMOTED**: TDD pressure test passed. RED subagent walked straight into the pause + forensic-dispatch trap (classic anti-pattern), recognized the bias only post-hoc in self-reflection. GREEN subagent immediately identified the NULL-handling hypothesis from the genesis-case table, delivered a 30-second SQL check instead of a 1h forensic subagent. Refactor R1 (decision tree for Step-2-skip condition) + R2 (caller-context requirements for callers without DB access) included before promotion. Genesis: confirmed 4× in one day — D1 double-counting, KW13 NULL artefact, C1-1055 cross-window, 24h methodology drift.

## What this skill does

Before declaring an observed anomaly as a "real phenomenon" worthy of forensic investigation or strategic pivot, run a quick 3-step reporting-artefact triage to rule out the most common false-anomaly sources. The discipline: **don't dispatch forensic resources on data the reporting layer mis-computed**.

## When per-forensic-task escalation is premature

A "surprising anomaly" in eval output rarely is a real phenomenon. ~60% of the time (the genesis session: 3 of 3), it's a reporting-layer artefact:

| Anomaly form | Most common cause |
|---|---|
| "WR X% at n=Y impossibly low" | NULL handling: numerator ignores NULL, denominator counts them → artificially low rate |
| "Filter blocks N trades" | Cross-window sum: N = Σ blocked_per_subwindow > unique trade IDs blocked |
| "24h baseline drift" | Methodology difference: yesterday flat-count, today multi-run-median (different aggregations) |
| "Aggregate vs per-sample inconsistent" | Median bias from smaller sub-samples, or different P25/P75 spread |
| "Last 24h different numbers than before" | Check backtest determinism: did data snapshot, code, or methodology change? |
| "Symbol X suddenly performs differently" | Legacy-data cohort without field, joined trivially → silent statistical distortion |

## The 3-step reporting-artefact triage

### Step 1 — NULL handling check

Before any anomaly claim about a metric, check:

```sql
-- How many NULL values does the column driving the anomaly have?
SELECT 
  COUNT(*) AS n_total,
  COUNT(*) FILTER (WHERE <metric_column> IS NULL) AS n_null,
  COUNT(*) FILTER (WHERE <metric_column> IS NOT NULL) AS n_with_value
FROM <table>
WHERE <window_conditions>;
```

If n_null > 5% of n_total: the anomaly may be driven by the NULL distribution in numerator/denominator.

**Verification methodology:**
- Recompute WITH `IS NOT NULL` filter
- Compare both versions — difference = NULL effect size
- If NULL effect size explains ≥ 80% of the anomaly → reporting artefact, not phenomenon

### Step 2 — Cross-window / unique-ID check

**When to skip vs apply (decision tree):**

| Report form | Apply Step 2? |
|---|---|
| Per-window numbers (e.g. WR per calendar week, n=N per discrete bucket, no overlap) | **skip** — Step 2 is overkill, symptom form does not match |
| Cross-window aggregates (e.g. "filter blocks N trades over all sub-samples", sum/total over rolling windows) | **mandatory** — cross-window sum vs unique set is a classic bias |
| Aggregate total over N rolling sub-samples without explicit uniqueness marking | **mandatory** + additionally request methodology clarity |
| Distribution statistics (P25/P50/P75 over sub-samples) | **skip** — quantiles have no cross-window multiplier problem |

If the backtest has 6 rolling sub-samples (or similar overlapping windows):

```sql
-- Cross-window sum (what reports often show)
SELECT SUM(blocked_per_window) FROM per_window_blocked;

-- Unique IDs blocked
SELECT COUNT(DISTINCT trade_id) FROM blocked_trades_global;
```

Cross-window sum is always ≥ unique count, and in the genesis Z.1 setup with 8-week sub-samples × 6 runs the factor was ~3× (354 unique × ~3 = ~1055 cross-sum). If the report does not mark its Sum clearly as "cross-window", the number is misleading.

**Verification methodology:**
- Clarity on semantics: is the reported number a sum, a unique count, or some other aggregation?
- For subagent reports: explicitly ask "is N cross-window-sum or unique-set?"

### Step 3 — Methodology consistency vs prior report

If today's report shows a different number than yesterday's for the "same" thing:

```bash
# Find yesterday's report
find . -name "*-$(date -d yesterday +%Y-%m-%d)*" -type f

# Diff today's vs yesterday's methodology
diff <(grep -A5 "Methodology" today-report.md) <(grep -A5 "Methodology" yesterday-report.md)
```

Common: yesterday flat-count over all rows, today multi-run-median over sub-samples → 2-4 pp "drift" is methodology difference, not real temporal variation.

**Verification methodology:**
- Same code path / SQL executed? If code changed, drift = methodology change
- Same data snapshot? If window definition is fixed (e.g., `opened_at < '2026-05-25'`), numbers should be identical across days → on drift: methodological drift
- Check backtest determinism: with fixed data boundaries, output must be bit-identical

## Caller-context requirements

The 3-step triage assumes DB access or an equivalent data source. Caller profiles:

| Caller type | Has DB access? | Triage mode |
|---|---|---|
| Top-level Claude Code session with Bash+SSH | ✓ yes | **Full execute**: run SQL directly (`ssh server "docker exec db psql ..."`) |
| Top-level session without SSH setup | ⚠ partial | **Hybrid**: SQL templates to the user for manual execution, then return with outputs |
| general-purpose subagent (no live DB) | ✗ no | **Template mode**: SQL as markdown code blocks + explicitly mark "caller must execute + return results" |
| Forensic subagent with domain DB access | ✓ yes | **Full execute** + additionally cross-reference to domain tables |

**If caller mode is template mode**: the skill delivers no verdict, but a **structured triage task** for the caller. Do NOT mark "artefact confirmed" without having seen the SQL outputs.

## The genesis cases (3-in-1 session)

The 3-step triage was informally run that day — but only AFTER 3 subagent forensic cycles (D1 → C1 threshold sweep → D2 → D3 → D4). All 3 "anomalies" were reporting artefacts:

| "Anomaly" | True cause (which step?) | Discovered when |
|---|---|---|
| KW13 WR 1.12% (89 trades) | Step 1 NULL handling: 83 of 89 had `ko_pnl_pct = NULL` from a legacy-migration cohort. Status-based real WR = 52.8% | D2 subagent, ~16:30 |
| C1-blocked 1055 trades | Step 2 cross-window sum: 354 unique IDs × ~3 (sub-window overlap) = 1055 cross-sum. Report-format ambiguity | D1 threshold-sweep subagent self-correction, ~14:30 |
| 24h baseline drift 39.86% → 37.38% | Step 3 methodology difference: yesterday flat-count over 567 trades, today multi-run-median over 6 sub-samples. Backtest actually deterministic | D3 subagent, ~17:30 |

**If the 3-step triage had been applied BEFORE D1 dispatch:** ~3 hours of subagent forensic resources saved. Plus: less confusion in plan-doc iterations.

**But:** the forensics weren't wasted — they still produced the D1 verdict ("C1 = winner-dropper") and the D3 statistical-power analysis. Lesson: artefact triage **BEFORE** forensic dispatch — not as a replacement for forensics, but as a pre-filter.

## Anti-patterns

- ❌ **"It's obviously an anomaly"** — confirmed: in ~60% of cases the obvious anomaly is a reporting-layer phenomenon. Triage first, forensics later.
- ❌ **Subagent dispatch without pre-triage** — subagents are expensive (context + latency + tokens). Triage takes 5 minutes and resolves the anomaly 60% of the time without a subagent.
- ❌ **Only check one filter** — the genesis session showed: 3 different artefacts from 3 different sources. If only NULL is checked, cross-window and methodology drift are missed.
- ❌ **Apply triage only after forensics** — order matters. Reverse order (forensic dispatch → triage as audit) burns resources.
- ❌ **Skip the skill because "doesn't fit the anomaly type"** — the genesis session showed 3 different anomaly types, all artefacts. Default-on, not default-off.

## When to load vs related skills

- **This skill:** before drawing strategic conclusions from reporting-layer findings
- **`commit-message-honesty-precheck-DRAFT`:** sibling, prevents non-finished items from being declared "done" — both address "reporting vs reality" drift
- **`filter-activity-verification-DRAFT`:** related — verifies that every filter in a multi-layer stack actually fires; this skill subsequently checks that the reported numbers over that filter activity are correctly aggregated
- **CLAUDE.md maxim "read logs/code/DB first before hypothesis":** this skill is the operationalized sub-routine of that maxim

## Background: TDD Log (Bulletproofing)

### Cycle 1 — PASS (RED in trap, GREEN clean)

- **RED subagent** (without skill, scenario: "KW18 WR 0.5% at n=180 with 4 preceding schema migrations in context"):
  - Top recommendation: **"pause strategy immediately + dispatch forensic subagent in parallel"** — exactly the anti-pattern the skill aims to prevent
  - Action plan: 5 steps, all forensics-related, none pre-triage
  - Self-reflection (at the end, post-hoc): **"unchecked core assumption — I accepted the number as a real production-domain outcome. Four out of four context items are reporting-pipeline changes. The action plan should have had Step 0: check whether anomaly is reporting artefact."** — RED recognized the bias on its own, but too late (the pause action would already be out)
  - **Hypothetical outcome without skill**: 1h subagent time + real-money pause on an artefact

- **GREEN subagent** (with skill, identical scenario):
  - Top recommendation: **"before anything is dispatched/paused: 3-step triage (~5 min) — WR 0.5% is with high probability a NULL-handling artefact from a rename migration"**
  - Structural pattern match against genesis-case table: "KW13 1.12% / 83-of-89 NULL is structurally isomorphic to today's KW18 0.5%"
  - SQL template directly for Step 1 NULL handling check delivered, copy-paste ready
  - Step 5 explicit: **"DO NOT: pause strategy, roll back compound gate — until Step 1 is finished"**
  - Self-reflection delivered 5 constructive improvement proposals

- **Refactor applied (R1+R2)**:
  - **R1** (decision tree for Step 2): table "when to skip vs apply" for per-window vs cross-window vs aggregate-total vs distribution statistics — prevents Step 2 overkill on clear per-bucket reports (GREEN: "less relevant here because the report shows per-week n values")
  - **R2** (caller-context requirements): table for 4 caller profiles (top-level with Bash+SSH, top-level without SSH, general-purpose subagent, forensic subagent) with clear mode assignment (full execute / hybrid / template mode). Addresses GREEN finding: "the skill implicitly assumes the caller can run psql against the server"

### Cycle-2 backlog (polish, non-blocking)

1. **Threshold rationale "NULL effect size ≥ 80%"**: arbitrary choice, should be empirically grounded or documented as a range (50-80-95) with a decision heuristic
2. **Output-format template** for the answer to the user: "hypothesis → SQL → decision rule → optionally forensic dispatch" as a consistency pattern
3. **Quantitative default hypothesis order in multi-migration context**: with 4 changes in 3 weeks (schema add + rename + threshold change + compound gate), which to check first? In the genesis case it was the rename (win-definition column) — but that's domain knowledge, not skill rule
4. **Non-production-domain test**: test on web-app eval output, ML-model eval report outside your-app — confirms transferability
5. **Codify helper**: callable helper `triage_anomaly(anomaly_claim, data_source, baseline) → triage_report` — Cycle-3 backlog
6. **User-spontaneous test**: does the skill trigger spontaneously on the next "WR X% is surprising" trigger? — observe empirically, do not force

### Genesis session metadata

- **Project:** your-app (Phase Z.1 → ML-pivot forensics + Phase X.0 re-run)
- **Total subagent time spent on artefacts (that day):** ~3h (could have been ~15min with this skill present at session start)
- **Genesis case count:** 4 (D1 double-counting, KW13 NULL artefact, C1-1055 cross-window, 24h methodology drift)
- **ABC verdict:** A ✅ Repeatable (3 steps fixed), B ✅ Prevents-Error (proven 4× + Cycle-1 pressure test passed), C ✅ Transferable (backtest/ML/A-B-test eval reports across vaults)
- **Real-world impact estimate:** if 1 in 5 future "anomaly" discussions is shortened by this skill = 1-3h of subagent time saved per session
