---
name: compound-gate-over-single-metric
description: Use when designing or reviewing a Go/No-Go-Gate, Backtest-Acceptance-Threshold, ML-Model-Promotion-Criterion, A/B-Test-Verdict, or any binary-decision-rule that triggers a downstream-action (deploy, promote, ship, reject) based on a single metric (especially WR/Accuracy/Recall/F1/CTR). Single-metric gates have a well-documented failure mode: false-positive accepts — the system clears the gate while a hidden dimension regresses catastrophically. Compound-Gate (≥2 metrics with AND-conjunction) closes this hole. Trigger phrases like "WR-Gate-Verdict", "Backtest-Go-No-Go", "Accuracy-Threshold", "Recall-Gate", "55% threshold", "Model-Promotion-Criterion", "A/B-Verdict-Rule", "single-metric Acceptance". Do NOT load for domain-establishment where single-metric meaningfulness is established and unambiguous (e.g. medical-test-sensitivity for binary screening, latency-SLO for infrastructure), for theoretical-discussions without downstream-action-consequence, or for cases where the second-dimension is already implicitly captured in the metric (e.g. precision-recall-F1 already trades off two dimensions).
---

# compound-gate-over-single-metric

> ✅ **PROMOTED**: RED-Subagent recognized the sample-size problem and missing metrics independently — good baseline. GREEN-Subagent explicitly applied all 3 compound dimensions, identified missing AvgPnL/Throughput as auto-NO-GO due to incomplete data basis, and gave attribution "why NO-GO" instead of just "NO-GO".

## What this skill does

When designing or evaluating a binary acceptance-gate, force at least 2 dimensions of evaluation with AND-conjunction. Single-metric gates have a structural failure mode: false-positive accept on hidden-regression in unsampled dimensions.

## Incomplete Data → Auto-NO-GO

**When a required dimension is missing (no AvgPnL given, no throughput baseline):**

→ **NO-GO due to incomplete data basis.** Not "Conditional-Go" — the gate cannot be cleared with unknown dimensions.

Reason: AND-conjunction means `PASS AND PASS AND PASS`. An `UNKNOWN` is not `PASS`. The missing dimensions must be collected first before the gate can be evaluated.

## The 3 failure modes of single-metric gates

### 1. Hidden-dimension regression

**Example:** Trading-Strategy-Backtest with Gate = WR ≥ 55%.
- Strategy A: WR 56%, AvgPnL +0.5%, Throughput 30% → PASS gate, but realized P&L marginal
- Strategy B: WR 50%, AvgPnL +3.0%, Throughput 50% → FAIL gate despite better economic substance

### 2. Sample-size-confounding

**Example:** ML-Model-Promotion-Gate = Accuracy ≥ 0.65.
- Model X: 65.2% accuracy on n=15 → PASS gate, but ±12pp confidence-interval
- Model Y: 62.0% accuracy on n=85 → FAIL gate, but ±5pp CI

Compound (Accuracy ≥ 0.62 AND n_eval_samples ≥ 50) prevents cherry-picking on small samples.

### 3. Cost-of-false-positive ignored

**Example:** A/B-Test-Gate = CTR_B > CTR_A.
- Variant B: CTR +0.3pp, but checkout-completion -5%
- A/B-Gate measures only CTR → ships B → revenue drops

## When single-metric IS sufficient

- **Latency-SLO:** p99 ≤ X ms — the single metric IS the user-visible-concern
- **Medical screening:** sensitivity ≥ X% — false-negative-cost is the only cost in this stage
- **Binary safety:** zero-violations — single binary metric is the whole semantic

The compound-skill applies when the single-metric is a **PROXY for an unstated joint-criterion**.

## Pattern: 3-Dimensional Compound-Gate

For any Trading-Backtest or ML-Strategy-Eval that produces a kept-trades subset:

| Dimension | Why it matters | Typical threshold |
|---|---|---|
| **Effectiveness** (WR / Accuracy) | Does the strategy find true positives? | ≥40% (or domain-baseline + 5pp) |
| **Economic value** (AvgPnL / Expected-Value) | Are true positives worth more than false-negatives? | ≥ +2% per trade (or > breakeven net fees) |
| **Operating-frequency** (Throughput / Coverage) | Does it fire enough to compound, or cherry-pick? | ≥ 30% of baseline volume |

Compound: Effectiveness ≥ X **AND** Economic ≥ Y **AND** Frequency ≥ Z.

**Verdict-Format:**
- All 3 PASS → GO-candidate
- All 3 FAIL → NO-GO
- Exactly 2 PASS → "Refine — failed because dimension X = value vs threshold Y"

Always emit per-dimension attribution, not just GO/NO-GO.

## The Genesis-Case

**Setup:** your-app Phase Z.1, Spec-Q4-Gate = WR ≥ 55%.

**Result:** WR-Median 39.98% (FAIL), Throughput 29.70% (PASS), AvgPnL −4.99%.

**Single-Metric verdict (WR-only):** NO-GO. Reason: "WR too low." Implication: "Tune filters to push WR higher."

**Compound-Gate verdict:** NO-GO. Reason: **"AvgPnL is negative — the filter DESTROYS winners. Pushing WR higher would worsen economic outcome further."** Implication: "Stop iterating on thresholds; investigate WHY filters drop winners."

Two verdicts agree on REJECT but disagree on **WHY**. The attribution drives the right next-step.

## Anti-patterns

- ❌ **Adding 5+ dimensions** — gates with many AND-conditions become impossible to clear. Max 3–4.
- ❌ **Weighting dimensions** (`0.6×WR + 0.3×AvgPnL`) — weighted-sum re-introduces hidden-regression. AND-conjunction is the discipline.
- ❌ **No per-dimension attribution** — "FAIL" without "because X = value vs threshold Y" loses diagnostic value.
- ❌ **Cargo-culting genesis-case-thresholds (40/2/30)** — those are empirically tied to trading-KO-strategies. Re-derive for your domain.

## Background: TDD log (Bulletproofing-Log)

### Cycle 1 (PASS)

- **RED-Subagent** (without skill): Recognized the sample-size problem at n=89 independently. Requested profit-factor, drawdown, slippage. Verdict: NO-GO. Reasoning correct, but structurally incomplete (no formal 3-class dimension, no AND-conjunction requirement).
- **GREEN-Subagent** (with skill): Explicitly applied all 3 compound dimensions. AvgPnL and Throughput missing → auto-NO-GO (DATA MISSING = not `PASS`). Emitted attribution with PASS/FAIL/DATA-MISSING per dimension. Recognized genesis-case analogy and wrote anti-pattern warning.
- **Refactor**: "Incomplete Data → Auto-NO-GO" section inserted as first block. Was missing in original.

### Cycle-2 backlog (non-blocking)

1. Callable evaluation helper: `evaluate_compound_gate(metric_dict, gates_dict) -> CompoundVerdict` with per-dimension attribution
2. Threshold-derivation methodology for 3 domains (trading, ML promotion, A/B test)
3. 2-of-3-PASS pressure test (refine case — most interesting calibration boundary)
