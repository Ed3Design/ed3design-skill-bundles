---
name: explicit-unknown-counter-vs-coalesce-mask
description: |-
  Use when writing aggregating SQL (SUM/AVG/COUNT) or Python-side aggregates over a NULL-able column where NULL means "data not present / not backfilled / unknown" (NOT "intentionally zero"). The naive `COALESCE(SUM(x), 0)` or `df.col.fillna(0).sum()` masks NULL-rows silently — drift goes undetected for weeks. Instead, ALWAYS pair the aggregate with an explicit `count(*) FILTER (WHERE col IS NULL)` Counter (Postgres) or `df.col.isna().sum()` (pandas), surfaced in the same response shape. Trigger phrases like "aggregate PnL", "monthly sum", "trade statistics", "NULL handling", "summary report with NULLable column", "why doesn't the aggregate match the memory", "drift in reporting". Do NOT load for columns where NULL is semantically zero (intentional NOT-NULL-DEFAULT-0 design — then COALESCE is correct), for non-aggregating queries (single-row SELECTs), or for transient runtime calculations where NULL means "in-flight" rather than "unknown".

---

# Explicit Unknown-Counter Instead of COALESCE-Mask

When aggregating over a NULLable column, the naive `COALESCE(SUM(x), 0)` is a **silent bug factory**: NULL-rows are quietly counted as zero and the aggregate looks correct to the caller. Drift goes undetected. Discovery comes weeks later via user pushback "why is the number X smaller than I expected?"

## When to use

- Reporting SQL with `SUM`, `AVG`, `COUNT(col)`, `MAX`, `MIN` over a column where NULL means "data not present"
- Backfill scenarios where some historical rows have NULL because the original write-path didn't populate the column yet
- API responses that must distinguish "value is 0" from "value is unknown"
- Pandas aggregates where `fillna(0)` is being used to "make it work"

## When NOT to use

- Columns where NULL is genuinely zero (e.g. `count_of_telegrams_sent` that's NOT-NULL-DEFAULT-0 at schema level — no NULLs possible)
- Single-row reads (a NULL is just NULL; caller handles it)
- Foreign-key columns where NULL means "no relation" (different semantics — use `IS NULL` joins)

## The pattern

### SQL (Postgres)

```sql
-- WRONG (silent NULL-mask)
SELECT COALESCE(SUM(realized_pnl_eur), 0) AS pnl_month
FROM v3_trades
WHERE closed_at >= date_trunc('month', now());

-- RIGHT (separate counter surfaces NULL-drift)
SELECT
    COALESCE(SUM(realized_pnl_eur), 0)::numeric(10,2) AS pnl_month_eur,
    count(*) FILTER (
        WHERE closed_at >= date_trunc('month', now())
        AND realized_pnl_eur IS NULL
    ) AS pnl_unknown_count
FROM v3_trades
WHERE closed_at >= date_trunc('month', now());
```

The response includes BOTH numbers. Consumer (Dashboard, /health/quick, daily report) shows them side-by-side: `PnL month -2.50€ (2 trades unknown)`.

### Pandas

```python
# WRONG
df.realized_pnl_eur.fillna(0).sum()

# RIGHT
{
    "pnl_sum_eur": df.realized_pnl_eur.sum(skipna=True),   # default skipna=True excludes NULL
    "pnl_unknown_count": df.realized_pnl_eur.isna().sum(),
}
```

### Why it matters — real example

The user had been seeing daily report PnL aggregates for weeks. Trade #14 (GOOG short) had `realized_pnl_eur=NULL` due to a close-bot DB-cast bug. The aggregate showed correct-looking numbers because `COALESCE` masked the NULL.

Later, a health-check phase introduced `closed_pnl_unknown` as an explicit counter — within ONE follow-up query, Trade #18 (IBE.MC short) was ALSO revealed to have `realized_pnl_eur=NULL`. That trade was completely unknown until the counter surfaced it.

**Counterfactual**: without the explicit counter, Trade #18's missing PnL would have stayed invisible until next month's manual reconciliation (memory estimate vs DB aggregate mismatch).

## Sibling pattern: surface in response shape

The counter must propagate INTO the API/Notification/Report response, not stay inside the SQL:

```python
return {
    "v3_trades": {
        "open": counts["open"],
        "closed_last_7d": counts["closed_last_7d"],
        "closed_pnl_unknown": counts["closed_pnl_unknown"],   # ← surfaced
        "pnl_month_eur": float(counts["pnl_month_eur"]),
    }
}
```

And in /health/quick summary-text:
```python
parts.append(f"PnL month {pnl_month:+.2f}€")
if pnl_unknown:
    parts.append(f"⚠ {pnl_unknown} trades unknown PnL")
```

## Anti-patterns

- ❌ `COALESCE(SUM(x), 0)` without companion counter → silent drift
- ❌ `df.col.fillna(0)` without `df.col.isna().sum()` log → same silent drift
- ❌ `if value is None: value = 0` in app-code before aggregating → moves the silent-mask one layer earlier
- ❌ NULL in the schema where the domain says "must be known" → DEFAULT 0 or NOT NULL CONSTRAINT instead; only use NULL when "unknown" is a semantic state
- ❌ Reporting the counter only in DEBUG-logs and not in the production payload → counter is invisible to the user, defeating the point

## Connection to other skills

- `reporting-artefact-detection-before-claiming-anomaly` (GA) — same family. Triage check #1 "NULL-Handling-Check" already mentions this pattern at the triage layer; this skill makes it preventive at the design layer.
- `enum-known-values-via-insert-grep` (GA) — also about silent drift, but on the enum-value axis (data domain) rather than NULL-axis.

## Background: TDD progress (Bulletproofing Log)

### Cycle 1 — PASS

- **RED subagent** (without skill, scenario: monthly balance for `v3_trades` with nullable `realized_pnl_eur`): Wrote naive query with `COUNT(*) AS closed_trades, SUM(realized_pnl_eur) AS total, AVG(realized_pnl_eur) AS avg`. Recognized the drift trap itself: **AVG denominator mismatch** (`AVG` uses divisor 2, `closed_trades=4` suggests divisor 4) + **win rate wrongly classifying NULL as loss** (`FILTER (WHERE realized_pnl_eur > 0)` with `COUNT(*)` denominator → 25% instead of 50%). Self-assessment: "No, the approach is NOT robust" — listed 4 concrete defects.

- **GREEN subagent** (with skill via Read tool, same task): Explicitly applied `closed_pnl_unknown` as counter, disambiguated `closed_trades_total` vs `closed_trades_with_pnl` in the response shape, and used `COUNT(realized_pnl_eur)` as win-rate denominator. Concrete example with 4 trades (2 NULL) showed correct reading "+75 EUR at 50% win rate over 2 trades, ⚠ 2 trades unknown PnL". Additionally developed a 5-point drift-detection strategy.

### Cycle-2 Backlog (Polish, non-blocking)

1. **Ratios over NULLable columns** as own sub-section — `COUNT(*)` vs `COUNT(col)` as denominator choice is its own drift risk
2. **Threshold alerts**: `closed_pnl_unknown > 0 AND age > 24h` → Telegram notification. Operational escalation of the pattern
3. **GROUP BY example** with `per symbol/month` — when grouping, a counter per group is needed
4. **Window-functions edge-case**: ROLLUP/CUBE behavior on NULL
5. **Empty-set behavior**: `SUM(NULL) over empty set` returns NULL, `COALESCE(SUM, 0)` returns 0 — when which?

## Cross-skill connections

- `reporting-artefact-detection-before-claiming-anomaly` (GA): NULL handling is triage step 1; this skill makes it mandatory
- `enum-known-values-via-insert-grep` (GA): silent drift on enum-value axis; this skill on NULL axis
- `read-only-sql-via-regex-validator` (GA): when aggregate queries come via API
