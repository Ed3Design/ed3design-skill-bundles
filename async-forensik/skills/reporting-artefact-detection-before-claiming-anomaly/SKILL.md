---
name: reporting-artefact-detection-before-claiming-anomaly
description: Use when observing a "surprising anomaly" in backtest output, SQL-query result, multi-run-eval-report, ML-model-performance-table, or any reporting-layer artefact that suggests a system-bug, market-outlier, methodological problem, or drift requiring investigation. Common forms: "WR X% bei n=Y ist katastrophal niedrig", "24h-Baseline-Drift +/-2pp", "Filter N hat seit gestern andere Numbers", "Sub-Sample-Median weicht von Aggregat-Total ab". Before treating the anomaly as a real phenomenon and dispatching forensik-resources to explain it, run a 3-step Reporting-Artefakt-Triage: (1) NULL-Handling-Check — werden NULL-Werte in Zähler/Nenner falsch behandelt? Wurde IS NOT NULL-Filter weggelassen? (2) Cross-Window/Unique-ID-Check — werden überlappende Sub-Windows / Joins / Aggregationen Trades mehrfach gezählt? Cross-Sum vs Unique-Count-Semantik klar? (3) Methodik-Konsistenz-Check zu Vorbericht — wurde dieselbe SQL/Berechnung exakt repliziert oder wurde subtil eine andere Aggregations-Methode benutzt? Drei Filter machen es leicht zu validieren BEVOR Forensik-Subagent dispatcht wird. Trigger phrases like "warum ist WR plötzlich so niedrig", "diese Anomalie verstehe ich nicht", "24h-Drift", "Baseline hat sich verändert", "Sub-Sample-Median überraschend", "Backtest gibt heute andere Numbers als gestern", "KW X war Katastrophe", "warum droppen die Numbers". Do NOT load for confirmed-real anomalies where the artefact-check is already done (then it's a real forensik-task, use domain-specific skills), for first-time-setup-debugging without baseline comparison (no Vorbericht to compare against), for non-reporting-layer issues like code-bugs in the algorithm itself (then it's debugging, not reporting-artefact-triage), or for user-facing UI-rendering-bugs (different domain). Encodes the 2026-06-02 ClaudetteV-Session-Discovery: three separate "anomalies" investigated over 4-hour-multi-subagent-forensik-cycle (KW13 WR 1.12%, C1-blocked 1055, 24h-Baseline-Drift 39.86→37.38) ALL turned out to be reporting-artefacts respectively due to (1) NULL-ko_pnl_pct in Legacy-Migrations-Kohorte ignored by WHERE-clause-filter-omission, (2) Cross-Window-Sum vs Unique-ID-Set semantic ambiguity, (3) Multi-Run-Median vs flat-count methodology difference between consecutive day reports. ~3 hours of subagent-forensik-resources spent on three artefact-validation-cycles that this 3-step check would have closed in 5 minutes each.

---

# reporting-artefact-detection-before-claiming-anomaly

> ✅ **PROMOTED 2026-06-02 (X.0-Closure-Session)**: TDD-Pressure-Test bestanden. RED-Subagent ging direkt in Pause+Forensik-Dispatch-Trap (klassisches Anti-Pattern), erkannte den Bias nur post-hoc in Self-Reflection. GREEN-Subagent identifizierte sofort NULL-Handling-Hypothese aus Genesis-Case-Tabelle, lieferte 30-Sekunden-SQL statt 1h-Forensik-Subagent. Refactor R1 (Decision-Tree für Step-2-Skip-Bedingung) + R2 (Caller-Context-Requirements für Caller-ohne-DB-Zugriff) eingebaut vor Promotion. Genesis: heute 4× bestätigt — D1-Double-Counting, KW13-NULL-Artefakt, C1-1055-Cross-Window, 24h-Methodik-Drift.

## What this skill does

Before declaring an observed anomaly as a "real phenomenon" worthy of forensik-investigation or strategic-pivot, run a quick 3-step Reporting-Artefakt-Triage to rule out the most common false-anomaly-sources. The discipline: **don't dispatch forensik-resources on data the reporting-layer mis-computed**.

## When per-forensik-task escalation is premature

A "surprising anomaly" in eval-output rarely is a real phenomenon. ~60% of time (heutige Session: 3 of 3), it's a reporting-layer artefact:

| Anomaly form | Most common cause |
|---|---|
| "WR X% bei n=Y unmöglich niedrig" | NULL-Handling: Zähler ignoriert NULL, Nenner zählt sie mit → künstlich niedrige Quote |
| "Filter blockt N Trades" | Cross-Window-Sum: N = Σ blocked_per_subwindow > unique-Trade-IDs blocked |
| "24h-Baseline-Drift" | Methodik-Differenz: gestern flat-count, heute Multi-Run-Median (verschiedene Aggregationen) |
| "Aggregate vs Per-Sample inkonsistent" | Median-Verzerrung durch kleinere Sub-Samples, oder anderer P25/P75-Spread |
| "Letzte 24h andere Numbers als vorher" | Backtest-Determinismus prüfen: hat sich Data-Snapshot, Code, oder Methodik geändert? |
| "Symbol X performt plötzlich anders" | Legacy-Daten-Kohorte ohne Field, joined trivially → silent statistical-distortion |

## The 3-step Reporting-Artefakt-Triage

### Step 1 — NULL-Handling-Check

Vor jeder Anomalie-Behauptung über eine Metric, prüfe:

```sql
-- Wie viele NULL-Werte hat die Spalte die zur Anomalie führt?
SELECT 
  COUNT(*) AS n_total,
  COUNT(*) FILTER (WHERE <metric_column> IS NULL) AS n_null,
  COUNT(*) FILTER (WHERE <metric_column> IS NOT NULL) AS n_with_value
FROM <table>
WHERE <window_conditions>;
```

Wenn n_null > 5 % von n_total: die Anomalie kann durch NULL-Verteilung in Zähler/Nenner getrieben sein.

**Verifizier-Methodik:**
- Berechnung erneut MIT `IS NOT NULL`-Filter
- Vergleich beider Versionen — Differenz = NULL-Effect-Size
- Wenn NULL-Effect-Size erklärt ≥ 80 % der Anomalie → Reporting-Artefakt, nicht Phänomen

### Step 2 — Cross-Window / Unique-ID-Check

**When to skip vs apply (Decision-Tree):**

| Report-Form | Apply Step 2? |
|---|---|
| Per-Window-Numbers (z.B. WR pro Kalenderwoche, n=N pro discrete Bucket, kein Overlap) | **skip** — Step 2 ist overkill, Symptom-Form passt nicht |
| Cross-Window-Aggregate (z.B. „Filter blockt N Trades over alle Sub-Samples", Sum/Total über rolling Windows) | **mandatory** — Cross-Window-Sum vs Unique-Set ist klassischer Bias |
| Aggregat-Total über N rolling Sub-Samples ohne explizite Unique-Markierung | **mandatory** + zusätzlich Methodik-Klarheit anfordern |
| Verteilungs-Statistiken (P25/P50/P75 über Sub-Samples) | **skip** — Quantile haben kein Cross-Window-Multiplikator-Problem |

Wenn Backtest 6 rolling Sub-Samples hat (oder ähnliche überlappende Windows):

```sql
-- Cross-Window-Sum (was Reports oft zeigen)
SELECT SUM(blocked_per_window) FROM per_window_blocked;

-- Unique-IDs blockiert
SELECT COUNT(DISTINCT trade_id) FROM blocked_trades_global;
```

Cross-Window-Sum ist immer ≥ Unique-Count, und in heutigem Z.1-Setup mit 8-Wochen-Sub-Samples × 6 Runs der Faktor ~3× (354 unique × ~3 = ~1055 cross-sum). Wenn Report Sum nicht klar als „cross-window" markiert ist, ist die Number missverständlich.

**Verifizier-Methodik:**
- Klarheit über Semantik: ist die berichtete Number Sum, Unique-Count, oder eine andere Aggregation?
- Bei Subagent-Reports: explicit ask „is N cross-window-sum or unique-set?"

### Step 3 — Methodik-Konsistenz-zu-Vorbericht

Wenn der heutige Report eine andere Number zeigt als gestern für „gleiche" Sache:

```bash
# Find yesterday's report
find . -name "*-$(date -d yesterday +%Y-%m-%d)*" -type f

# Diff today's vs yesterday's methodology
diff <(grep -A5 "Methodik" today-report.md) <(grep -A5 "Methodik" yesterday-report.md)
```

Häufig: Yesterday flat-count over all rows, Today Multi-Run-Median über Sub-Samples → 2-4 pp „Drift" ist Methodik-Differenz, nicht echte temporale Variation.

**Verifizier-Methodik:**
- Gleiche Code-Pfad / SQL ausführen? Wenn Code geändert wurde, Drift = Methodik-Change
- Gleiche Data-Snapshot? Wenn Window-Definition fix ist (e.g., `opened_at < '2026-05-25'`), sollten Numbers über Tage identisch sein → bei Drift: methodologische Drift
- Backtest-Determinismus prüfen: bei fixen Daten-Boundaries muss Output bit-identisch sein

## Caller-Context Requirements

Die 3-Step-Triage setzt DB-Zugriff oder eine äquivalente Daten-Quelle voraus. Caller-Profile:

| Caller-Typ | Hat DB-Zugriff? | Triage-Modus |
|---|---|---|
| Top-Level Claude Code Session mit Bash+SSH | ✓ ja | **Full-Execute**: SQL direkt laufen lassen (`ssh server "docker exec db psql ..."`) |
| Top-Level Session ohne SSH-Setup | ⚠ partiell | **Hybrid**: SQL-Templates an User für manuelle Execution, dann mit Outputs zurück |
| general-purpose Subagent (kein Live-DB) | ✗ nein | **Template-Mode**: SQL als Markdown-Code-Blocks zurück + explizit „Caller muss ausführen + Ergebnisse zurückgeben" markieren |
| Forensik-Subagent mit Domain-DB-Zugriff | ✓ ja | **Full-Execute** + zusätzlich Cross-Reference zu Domain-Tabellen |

**Wenn Caller-Modus Template-Mode**: das Skill liefert kein Verdict, sondern eine **strukturierte Triage-Aufgabe** für den Caller. NICHT eigenmächtig „Artefakt bestätigt" markieren ohne die SQL-Outputs gesehen zu haben.

## The 2026-06-02 Genesis-Cases (3-in-1 Session)

Heute wurde diese 3-Step-Triage informell durchgezogen — aber erst NACH 3 Subagent-Forensik-Cycles (D1 → C1-Threshold-Sweep → D2 → D3 → D4). Alle 3 „Anomalien" waren Reporting-Artefakte:

| "Anomaly" | True Cause (welcher Step?) | Discovered when |
|---|---|---|
| KW13 WR 1.12 % (89 Trades) | Step 1 NULL-Handling: 83 von 89 hatten `ko_pnl_pct = NULL` aus Legacy-Migrations-Kohorte. Status-basierter echter WR = 52.8 % | D2 Subagent, ~16:30 |
| C1-blocked 1055 Trades | Step 2 Cross-Window-Sum: 354 unique IDs × ~3 (Sub-Window-Overlap) = 1055 cross-sum. Report-Format-Ambiguität | D1-Threshold-Sweep-Subagent self-correction, ~14:30 |
| 24h-Baseline-Drift 39.86 % → 37.38 % | Step 3 Methodik-Differenz: gestern flat-count über 567 Trades, heute Multi-Run-Median über 6 Sub-Samples. Backtest tatsächlich deterministisch | D3 Subagent, ~17:30 |

**Wenn die 3-Step-Triage VOR D1-Dispatch angewandt worden wäre:** ~3 Stunden Subagent-Forensik-Resources gespart. Plus: weniger Konfusion in Plan-Doc-Iterationen.

**Aber:** Die Forensik war nicht umsonst, weil sie D1-Verdict („C1 = Winner-Dropper") und D3-Statistical-Power-Analyse trotzdem brachte. Lesson: Artefakt-Triage **VOR** der Forensik-Dispatch — nicht als Ersatz für Forensik, sondern als Pre-Filter.

## Anti-patterns

- ❌ **„Es ist offensichtlich eine Anomalie"** — heute bestätigt: in ~60 % der Fälle ist die offensichtliche Anomalie ein Reporting-Layer-Phänomen. Erst Triage, dann Forensik.
- ❌ **Subagent dispatch ohne Pre-Triage** — Subagents sind teuer (Kontext + Latency + Tokens). Triage ist 5 Minuten und löst die Anomalie 60 % der Zeit ohne Subagent.
- ❌ **Nur einen Filter prüfen** — heute zeigte: 3 verschiedene Artefakte aus 3 verschiedenen Sources. Wenn nur NULL gecheckt wird, fehlt Cross-Window und Methodik-Drift.
- ❌ **Triage erst nach Forensik anwenden** — die Reihenfolge matters. Reverse-Order (Forensik dispatch → Triage as audit) verbrennt Resources.
- ❌ **Skill skippen weil „nicht zum Anomaly-Typ"** — heute zeigte 3 verschiedene Anomaly-Typen, alle Artefakte. Default-an, nicht Default-aus.

## When-to-load vs related skills

- **This skill:** vor dem Treffen von strategischen Schlüssen aus Reporting-Layer-Befunden
- **`commit-message-honesty-precheck-DRAFT`:** sibling, verhindert dass nicht-erledigte Items als „done" deklariert werden — beide adressieren „Reporting-vs-Reality"-Drift
- **`filter-activity-verification-DRAFT`:** verwandt — verifiziert dass jeder Filter im Multi-Layer-Stack tatsächlich feuert; dieses Skill prüft NACHFOLGEND dass die berichteten Numbers über diese Filter-Activity korrekt aggregiert sind
- **CLAUDE.md-Maxime „erst Logs/Code/DB lesen vor Hypothese":** dieses Skill ist die operationalisierte Sub-Routine dieser Maxime

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-02 (PASS — RED in Trap, GREEN clean)

- **RED-Subagent** (ohne Skill, Scenario: „KW18 WR 0.5% bei n=180 mit 4 vorhergehenden Schema-Migrationen im Kontext"):
  - Top-Empfehlung: **„Strategie sofort pausieren + parallel Forensik-Subagent dispatchen"** — exakt das Anti-Pattern das Skill verhindern soll
  - Action-Plan: 5 Schritte, alle Forensik-bezogen, keiner Pre-Triage
  - Self-Reflection (am Ende, post-hoc): **„Ungeprüfte Kernannahme — ich habe die Zahl als reales Trading-Outcome akzeptiert. Vier von vier Kontext-Items sind Reporting-Pipeline-Changes. Action-Plan hätte Step 0 sein müssen: prüfe ob Anomalie Reporting-Artefakt ist."** — RED erkannte den Bias selber, aber zu spät (Pause-Aktion wäre schon raus)
  - **Hypothetischer Outcome ohne Skill**: 1h Subagent-Time + Real-Money-Pause auf einem Artefakt

- **GREEN-Subagent** (mit Skill, identisches Scenario):
  - Top-Empfehlung: **„Bevor irgendwas dispatched/pausiert: 3-Step Triage (~5 Min) — WR 0.5% ist mit hoher Wahrscheinlichkeit NULL-Handling-Artefakt aus Rename-Migration"**
  - Strukturelles Pattern-Matching auf Genesis-Case-Tabelle: „KW13 1.12% / 83-of-89 NULL ist strukturell isomorph zu heutiger KW18 0.5%"
  - SQL-Template direkt für Step 1 NULL-Handling-Check geliefert, copy-paste-ready
  - Step 5 explizit: **„NICHT: Strategie pausieren, Compound-Gate rollbacken — solange Step 1 nicht durch ist"**
  - Self-Reflection lieferte 5 konstruktive Verbesserungs-Vorschläge

- **Refactor angewendet (R1+R2)**:
  - **R1** (Decision-Tree für Step 2): Tabelle „When to skip vs apply" für Per-Window vs Cross-Window vs Aggregat-Total vs Verteilungs-Statistiken — verhindert Step-2-Overkill bei klaren Per-Bucket-Reports (GREEN: „Hier eher weniger relevant weil Report Per-Woche n-Werte zeigt")
  - **R2** (Caller-Context Requirements): Tabelle für 4 Caller-Profile (Top-Level mit Bash+SSH, Top-Level ohne SSH, general-purpose Subagent, Forensik-Subagent) mit klarer Modi-Zuordnung (Full-Execute / Hybrid / Template-Mode). Adressiert GREEN-Befund: „Skill geht implizit davon aus dass Caller psql gegen Server fahren kann"

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Schwelle-Begründung "NULL-Effect-Size ≥ 80%"**: arbitrary Wahl, sollte empirisch belegt oder als Range (50-80-95) mit Decision-Heuristik dokumentiert sein
2. **Output-Format-Template** für die Antwort an den User: „Hypothese → SQL → Decision-Rule → ggf. Forensik-Dispatch" als Konsistenz-Pattern
3. **Quantitative Default-Hypothese-Reihenfolge bei Multi-Migration-Kontext**: wenn 4 Änderungen in 3 Wochen (Schema-Add + Rename + Threshold-Change + Compound-Gate), welche zuerst checken? Heute war es das Rename (Win-Definitions-Spalte) — aber das ist Domain-Wissen, nicht Skill-Regel
4. **Non-Trading-Domain-Test**: Test auf Web-App-Eval-Output, ML-Model-Eval-Report außerhalb ultimative-platform — bestätigt Transferability
5. **Codify Helper**: callable helper `triage_anomaly(anomaly_claim, data_source, baseline) → triage_report` — Cycle-3-Backlog
6. **Wolf-Spontan-Test**: läuft das Skill spontan beim nächsten „WR X% ist überraschend" Trigger? — empirisch beobachten, nicht erzwingen

### Genesis-Session Metadata

- **Date:** 2026-06-02 (X.0-Closure-Session abends)
- **Vault:** ClaudetteV
- **Project:** ultimative-platform (Phase Z.1 → ML-Pivot-Forensik + Phase X.0 Re-Run)
- **Total Subagent-Time spent on artefacts (heute):** ~3h (could have been ~15min with this skill present at session-start)
- **Genesis-Case-Count heute:** 4 (D1-Double-Counting, KW13-NULL-Artefakt, C1-1055-Cross-Window, 24h-Methodik-Drift)
- **ABC-Verdict:** A ✅ Repeatable (3 Schritte fest), B ✅ Prevents-Error (heute 4× bewiesen + Cycle-1-Pressure-Test bestanden), C ✅ Transferable (Backtest-/ML-/A/B-Test-Eval-Reports vault-übergreifend)
- **Real-world impact estimate:** Wenn 1 von 5 künftigen „Anomaly"-Diskussionen durch dieses Skill abgekürzt wird = 1-3h Subagent-Time-Saving pro Session
