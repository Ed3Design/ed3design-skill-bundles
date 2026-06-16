---
name: external-advisor-output-plausibility-audit
description: |-
  Use when an externally-commissioned advisor output (energy-consultant roadmap/iSFP, PV quote, renovation quote, tax-advisor note, expert report, investment recommendation) needs evaluation — do NOT accept the numbers at face value, run a structured 5-step audit: (1) inventory reality-check, (2) sequence/legal-check against applicable law, (3) cost/market-check against realistic values, (4) completeness-check (implied-but-not-costed components), (5) motive-check (advisor incentives, double application, kickback risk). In one real case this surfaced 6 technical defects plus an apparent subsidy-fraud construct. Trigger on phrases like "review this iSFP", "run the numbers on this quote", "the tax advisor says", "how should I evaluate this offer", "should I adopt this proposal". Do NOT load for the user's own data analysis, for pure market research (no concrete offer), or for legally-mandated expert reports (structural engineer, chimney sweep — a different audit mode).
---

# external-advisor-output-plausibility-audit

## Pattern (short form)

For external advisor outputs (energy consultant, PV planner, tax advisor, investment advisor, expert) ALWAYS run a structured 5-point audit before accepting the recommendation:

1. **Inventory reality-check** — does the data the advisor collected match reality?
2. **Sequence/legal-check** — do the proposed measures/sequences violate applicable law?
3. **Cost/market-check** — are the investment and "would-have-paid-anyway" costs realistic?
4. **Completeness-check** — are components implied in the concept but not costed?
5. **Motive-check** — does the advisor have incentives that drive certain recommendations?

Worked example (an energy-renovation roadmap / iSFP for a multi-family house): all 5 audit points produced critical findings; the most important was the **motive-check** (splitting the building into two applications for a double government subsidy).

## Audit step 1: inventory reality-check

Compare the data in the advisor output about the object/situation against:
- Other documents you already have (exposé, energy certificate, contracts, sensors)
- Real data if available (sensor recordings, utility statements, electricity bills)
- Your own records (measurements, notes)

**Checklist**:
```
☐ Building data (full storeys, floor area, year built) correct?
☐ Equipment data (heating type, capacity, year built) correct?
☐ Occupancy status (rented/empty, single- vs multi-family) correct?
☐ Prior renovation history (what was done when) correct?
☐ Energy-consumption data plausible? (check against real data!)
```

**Worked example — what went wrong**:
- The report claims "natural-gas boiler with hot-water tank" — doesn't exist (there's a shared oil heater)
- The report claims "currently vacant" — all 3 units are rented
- The report claims "2 full storeys" — there are 3
- Reported final energy use 91,000 kWh/a vs. tank-sensor 80,000 kWh/a (real data)

## Audit step 2: sequence/legal-check

Check whether the proposed measure-sequence and timeline are compatible with applicable law.

**For renovation recommendations** (German building-energy law, GEG, as an example jurisdiction):
- **§ 72 GEG** — mandatory replacement of constant-temperature oil/gas heaters after 30 years
- **§ 71 GEG** — 65%-renewables obligation for new heaters
- **§ 26 GEG** — air-tightness-test obligation for energy renovations
- **§ 47 GEG** — insulation obligation for the topmost ceiling
- **Subsidy conditions** — what is funded, what isn't, which constellations are excluded

**Worked example**:
- The report plans the heater replacement only for 2034-2037 — violates § 72 GEG (built 1998 → mandatory replacement 2028)
- The report recommends a 12-year sequence with 3-year intervals — administratively subsidy-oriented, technically suboptimal

## Audit step 3: cost/market-check

Check whether the stated investment and "would-have-paid-anyway" costs are realistic.

**Method**:
- Gross costs against market research (trade-association hourly rates, material market prices)
- "Would-have-paid-anyway" share against a plausible lower bound (e.g. for a monolithic wall: NOT 45% of the insulation cost as "anyway" for "render renewal")
- Subsidy rates against current status (they change often)
- Obtain comparison quotes (1-3 competing quotes are often instructive)

**Worked example**:
- Report exterior-wall "anyway" share 30,177 € on 70,479 € gross = 43% — far too high for a monolithic wall (realistically 15-20k€ for render renewal)
- Report heating "anyway" share 27,816 € on 54,606 € = 51% — fits a conventional heating renewal ✓

## Audit step 4: completeness-check

Which components are mentioned in the concept but not costed? Which are missing entirely?

**Typical completeness gaps in renovation concepts**:
- PV system mentioned but no investment package
- Heat-pump recommendation without considering radiator replacement (flow-temperature problem)
- EV charging infrastructure ignored
- Tenant-electricity model not discussed
- Profitability calculation without tax effects
- Energy savings computed without PV synergy

**Worked example**:
- The implementation guide mentions PV "to support the heat pump" — but the main plan has NO PV investment package
- Consequence: PV cost + subsidy + self-consumption profitability completely uncosted

## Audit step 5: motive-check (critical — often overlooked)

Could the advisor have incentives that drive certain recommendations?

**Possible advisor motives that distort the output**:
- **Double application** for more fees/subsidy (worked example: the split into two applications)
- **Commission ties** to certain manufacturers (PV brand, heat-pump brand, insulation maker)
- **Reuse of boilerplate recommendations** instead of individual assessment (copy-paste reports)
- **Avoidance of complex measures** the advisor can't handle themselves (e.g. tenant-electricity model, dual heat-pump sizing)
- **Preference for large investments** (higher fee with project supervision)
- **Confirmation bias** when the user already showed a tendency ("you wanted a heat pump, so we build the concept around it")

**Worked example — the smoking gun**:
- Two subsidy case-numbers for the same building
- The second report invents a "natural-gas boiler" to justify the split
- The second report falsely claims "vacant" — possibly to satisfy other subsidy criteria
- Subsidy cap: max 1,700 €/building → ~3,400 € extracted instead of 1,700 €

**→** The hunch that "the author split the building to get a double bonus" only became provable through the structured audit.

## Audit output pattern

After running the 5 audit steps: a **structured assessment note** with:

1. **Usable data** — what can be salvaged despite defects? (component specs, technically correct recommendations that stand independently)
2. **Critical defects** — sorted by severity
3. **Strategic recommendation** — keep / discard / complain / lawyer
4. **Email draft** (optional) if a complaint is warranted
5. **Archiving marker** — as evidence documentation if needed later

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| "The advisor has a certificate — it'll be fine" | Certificates are an entry threshold, not per-output quality proof |
| "The numbers look plausible" → adopt | A plausibility impression isn't enough; check against real data |
| "Subsidy rates are in the report — so they're correct" | Subsidy rates change often; verify against the current status |
| Skip the motive-check with "sounds a bit paranoid" | The motive-check uncovers the most important findings (see the subsidy-fraud case) |
| Doing only points 1-3, omitting 4+5 | Completeness- + motive-check are the most valuable — and the most often skipped |

## When to apply / when not

| Trigger | Apply skill? |
|---|---|
| External energy-renovation roadmap / iSFP present | ✅ yes, all 5 steps |
| PV quote from an installer | ✅ yes, focus on motive (brand ties) + completeness |
| Tax-advisor recommendation on depreciation / income statement | ✅ yes, focus on inventory + completeness |
| Investment-advisor proposal (funds, ETFs) | ✅ yes, focus on motive (commission/holdings) + cost |
| Architect planning | ⚠ partially — architects have professional-fee obligations, different audit mode |
| Legally-mandated expert report (structural/court expert) | ❌ no — formally obliged, different mode |
| Your own data analysis | ❌ no |
| Pure market research (no concrete offer) | ❌ no |

## Background

The pattern emerged from auditing two energy-renovation roadmaps (iSFPs) for a multi-family house that were suspected of being "technically flawed". The structured audit uncovered:
- 6 technical defects (inventory, legal violation, completeness)
- 1 subsidy-fraud construct (artificial split for a double government bonus)
- ~75,000 € of artificial extra cost through the split
- 5 smoking-gun false statements in the second report

Without the structured audit these problems would **not all have been found** — the gut feeling was right, but the concrete naming of the defects was only enabled by the 5-point audit.

**Real-world impact**:
- The report was reclassified from "usable with reservations" to "discard, new advisor"
- A complaint email with 7 defect points was drafted
- A requirements profile for a new energy advisor was created
- The report assessment was archived as evidence documentation
- The subsidy-clawback risk was made explicit

## Cross-references

- Complementary: `legal-paragraph-recommendation-checklist` — for the legal-check step

## Notes for skill reviewers

- Important caveat: the skill must not become too paranoid — some advisors deliver correct work. The audit is meant to be **structured skepticism**, not **automatic distrust**.
- A possible sub-cluster is a dedicated tax-advisor-output audit (different domain).

## Background: TDD log

### Cycle 1 (PASS)

- **RED subagent** (without skill, "should I adopt this iSFP?"): 3 heuristic points (consumption discrepancy, heating sequence seems reversed, "anyway"-share high). Recognized the §72 GEG rule from memory ("from memory — not verified via web search"), **omitted the motive-check entirely** (no bias-check of the advisor, no double-application hypothesis). Self-critique at the end: "my answer is a plausibility-driven sample, not a real audit".
- **GREEN subagent** (with skill, same prompt): All 5 audit steps applied explicitly. §72 GEG violation named sharply (mandatory replacement 2028, not 2034). The 43% "anyway"-share questioned structurally (realistically 15-20k€). Completeness-check identified the missing PV package + radiator replacement + tenant-cost logic. Motive-check pulled the subsidy case-numbers from the skill background → subsidy-fraud forensics. Strategic recommendation: **discard, new advisor**.
- **Verdict**: GREEN clearly superior. Skill is GA-ready. Refactor: only extended the trigger to include "should I adopt this iSFP" (execution side, not just intake).

### Cycle-2 backlog (polish, non-blocking)

1. **Severity scoring** per finding (🔴 critical / 🟡 important / 🟢 correctable) — makes the final strategic recommendation more compelling
2. **Step-3 market-research sources** named concretely (trade-association hourly-rate URL, subsidy-condition URL) instead of "against market research"
3. **Tax-advisor-audit sub-cluster** as a separate skill candidate if tax-advisor outputs need auditing often
