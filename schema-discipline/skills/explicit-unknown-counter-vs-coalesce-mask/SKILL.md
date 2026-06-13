---
name: explicit-unknown-counter-vs-coalesce-mask
description: Use when writing aggregating SQL (SUM/AVG/COUNT) or Python-side aggregates over a NULL-able column where NULL means "data not present / not backfilled / unknown" (NOT "intentionally zero"). The naive `COALESCE(SUM(x), 0)` or `df.col.fillna(0).sum()` masks NULL-rows silently — drift goes undetected for weeks. Instead, ALWAYS pair the aggregate with an explicit `count(*) FILTER (WHERE col IS NULL)` Counter (Postgres) or `df.col.isna().sum()` (pandas), surfaced in the same response shape. Trigger phrases like "PnL aggregieren", "Monatssumme", "Trade-Statistik", "NULL handling", "summary report mit NULLable column", "warum stimmt die Aggregatzahl nicht mit der Erinnerung überein", "Drift in Reporting". Do NOT load for columns where NULL is semantically zero (intentional NOT-NULL-DEFAULT-0 design — then COALESCE is correct), for non-aggregating queries (single-row SELECTs), or for transient runtime calculations where NULL means "in-flight" rather than "unknown".
---

# Explicit Unknown-Counter Instead of COALESCE-Mask

When aggregating over a NULLable column, the naive `COALESCE(SUM(x), 0)` is a **silent bug factory**: NULL-rows are quietly counted as zero and the aggregate looks correct to the caller. Drift goes undetected. Discovery comes weeks later via Wolf-Pushback "warum ist die Zahl X kleiner als ich erwartet hatte?"

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

The response includes BOTH numbers. Consumer (Dashboard, /health/quick, Daily-Note) shows them side-by-side: `PnL-Monat -2.50€ (2 trades unknown)`.

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

### Why it matters — real example (2026-06-11)

Wolf had been seeing Daily-Note PnL aggregates for weeks. Trade #14 (GOOG short, closed 27.05.) had `realized_pnl_eur=NULL` due to a close-bot DB-cast bug (29.05.). The aggregate showed correct-looking numbers because `COALESCE` masked the NULL.

On 11.06., `ultimative-health` Phase B introduced `closed_pnl_unknown` as an explicit counter — within ONE Phase-G query later, Trade #18 (IBE.MC short, closed 03.06.) was ALSO revealed to have `realized_pnl_eur=NULL`. That trade was completely unknown until Phase B's counter surfaced it.

**Counterfactual**: without the explicit counter, Trade #18's missing PnL would have stayed invisible until next month's manual reconciliation (Wolf-Brain estimate vs DB-aggregate mismatch).

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
parts.append(f"PnL-Monat {pnl_month:+.2f}€")
if pnl_unknown:
    parts.append(f"⚠ {pnl_unknown} trades unknown PnL")
```

## Anti-patterns

- ❌ `COALESCE(SUM(x), 0)` without companion counter → silent drift
- ❌ `df.col.fillna(0)` without `df.col.isna().sum()` log → same silent drift
- ❌ `if value is None: value = 0` in app-code before aggregating → moves the silent-mask one layer earlier
- ❌ NULL in the schema where the domain says "must be known" → DEFAULT 0 or NOT NULL CONSTRAINT instead; only use NULL when "unknown" is a semantic state
- ❌ Reporting the counter only in DEBUG-logs and not in the production payload → counter is invisible to Wolf, defeating the point

## Connection to other skills

- `reporting-artefact-detection-before-claiming-anomaly` (GA) — same family. Triage check #1 "NULL-Handling-Check" already mentions this pattern at the triage layer; this skill makes it preventive at the design layer.
- `enum-known-values-via-insert-grep` (GA) — also about silent drift, but on the enum-value axis (data domain) rather than NULL-axis.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill, Scenario: Monatsbilanz Juni 2026 für `v3_trades` mit nullable `realized_pnl_eur`): Schrieb naive Query mit `COUNT(*) AS closed_trades, SUM(realized_pnl_eur) AS total, AVG(realized_pnl_eur) AS avg`. Erkannte selbst die Drift-Falle: **AVG-Denominator-Mismatch** (`AVG` rechnet mit Divisor 2, `closed_trades=4` suggeriert Divisor 4) + **Win-Rate fälschlich klassifiziert NULL als Loss** (`FILTER (WHERE realized_pnl_eur > 0)` mit `COUNT(*)`-Denominator → 25% statt 50%). Self-Assessment: „Nein, der Approach ist NICHT robust" — 4 konkrete Mängel aufgezählt.

- **GREEN-Subagent** (mit Skill via Read-Tool, gleiche Aufgabe): Wandte explizit `closed_pnl_unknown` als Counter an, disambiguierte `closed_trades_total` vs `closed_trades_with_pnl` in der Response-Shape, und nutzte `COUNT(realized_pnl_eur)` als Win-Rate-Denominator. Konkretes Beispiel mit 4 Trades (2 NULL) zeigte korrekte Lesart „+75 EUR bei 50% Win-Rate über 2 Trades, ⚠ 2 trades unknown PnL". 5-Punkte-Drift-Erkennungs-Strategie zusätzlich entwickelt.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Ratios over NULLable columns** als eigene Sub-Sektion — `COUNT(*)` vs `COUNT(col)` als Denominator-Wahl ist ein eigenes Drift-Risiko
2. **Threshold-Alerts**: `closed_pnl_unknown > 0 AND age > 24h` → Telegram-Notification. Operative Eskalation des Patterns
3. **GROUP BY-Beispiel** mit `pro Symbol/Monat` — bei Gruppierung wird Counter pro Gruppe nötig
4. **Window-functions edge-case**: ROLLUP/CUBE behavior bei NULL
5. **Empty-Set-Verhalten**: `SUM(NULL) over empty set` returns NULL, `COALESCE(SUM, 0)` returns 0 — wann was?

## Cross-Skill-Connections

- `reporting-artefact-detection-before-claiming-anomaly` (GA): NULL-Handling ist Triage-Step 1; dieses Skill macht es zur Pflicht
- `enum-known-values-via-insert-grep` (GA): silent drift auf Enum-Value-Axis; dieses Skill auf NULL-Axis
- `read-only-sql-via-regex-validator` (GA): wenn die Aggregate-Queries via API kommen
