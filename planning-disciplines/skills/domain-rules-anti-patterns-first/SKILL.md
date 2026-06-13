---
name: domain-rules-anti-patterns-first
description: Use when modeling a domain that has formal legal/regulatory rules — pensions, taxes, insurance, employment law, inheritance law, social law, healthcare law, unemployment benefits/social benefits, contract law, civil code, tax code, social code, etc. Trigger on phrases like "calculate pension", "model tax", "insurance contribution", "entitlement to X", "qualifying period", "assessment basis", "retirement age", "deduction", "inheritance", "gift tax", "unemployment benefits", "old-age pension", "survivor's pension", "benefits suspension period", "one-fifth rule", "progression clause", "tax form V", "advertising costs", "special expenses", "allowance", "contribution assessment limit". Do NOT load for general programming domain modeling (database schemas, API contracts), for pure math/physics modeling (no legal/regulatory aspect), or for project-internal business logic where you are the rule-author. This skill encodes a pattern: when modeling a legal domain, the AI knows the POSITIVE rules from training but consistently misses the BLOCKING CLAUSES (anti-patterns, exceptions, traps). Result: 3+ user corrections in one session. Discipline: actively ask about the traps BEFORE coding the positive rules.
---

# Domain-Rules Anti-Patterns First

When modeling a legal/regulatory domain (pensions, taxes, insurance, social law etc.), the AI knows the positive entitlement/calculation/benefit rules reasonably well from training data. But the **blocking clauses** (anti-patterns, exceptions, traps, minimum requirements) — these are the rules where the AI is most likely to model incorrectly. They're often spread across multiple paragraphs of a statute, depend on specific personal constellations, and aren't part of typical "summary" content.

This skill exists because in a single pension-app session, three different anti-patterns had to be corrected that were initially missed:

1. **§51 para 3a SGB VI** — unemployment-benefit time does NOT count toward the 45-year qualifying period for "particularly long-time insured" (block against last-minute unemployment-benefit application)
2. **§166 SGB VI** — unemployment benefits DO accrue earnings points (these had been modeled as "negligible")
3. **§34 para 1 EStG** — one-fifth rule for severance with cheaper-option-check (would have been modeled as a pure tax break)

Plus methodologically related from earlier sessions: brand-foundation origin question (name origin: pet vs initial); multi-choice vs open-question style.

## When to use

- Modeling pension calculation (earnings points, qualifying periods, deductions, valuation factor, taxable portion)
- Modeling income tax (tariff formulas, allowances, special expenses, advertising costs, extraordinary income)
- Modeling insurance contributions / social security (health/care/pension/unemployment)
- Modeling inheritance/gift tax, allowances, tax classes
- Modeling contract-law constructs with statutory constraints
- Any "life-decision" app where a wrong calculation costs the user real money

## When NOT to use

- Generic programming domains (database design, API contracts, file formats) — no anti-patterns in the legal sense
- Pure math/physics modeling (statics, heat conduction, circuits) — natural laws without blocking clauses
- Internal business logic where you ARE the rule-author — you know the traps yourself
- Quick prototypes where accuracy doesn't matter — the skill discipline slows down meaningful iteration

## Iron rule

**Before implementing a positive calculation rule, explicitly ask about blocking clauses + anti-patterns + minimum requirements.**

Concrete question to the user:

> Before I implement this [pension/tax/insurance] calculation — do you know of any blocking clauses or special rules I need to consider? Specifically:
>
> 1. What conditions must be met (qualifying periods, contribution years, age, relationship status)?
> 2. Are there blocks that typically kick in "shortly before the goal" (blocking last-minute strategies)?
> 3. What special rules apply to special cases (special supply, regional valuation, severe disability etc.)?
> 4. Is there a "cheaper-option check" or choice between several procedures?

The user knows this from their own pension statements, tax assessments, contracts with tax advisors or self-research — they have the relevant domain knowledge that the positive calculation alone does not capture.

## Domain-specific cheat sheets — typical anti-patterns

### Pensions (SGB VI — German pension code) — typical blocks

| Block | Paragraph | Effect |
|---|---|---|
| 45-year qualifying period for particularly long-time insured | §51 para 3a SGB VI | Unemployment-benefit time does NOT count (max the last 2 years before pension) |
| Early old-age pension long-time insured | §236 SGB VI | Deduction 0.3% per month before regular retirement age (max 14.4%) |
| Postponing past regular retirement age | §77 SGB VI | Bonus 0.5% per month (max not capped) |
| Pension splitting on divorce | §76 SGB VI | EP transfer on divorce, permanent (no "reversal" if ex-spouse dies before pension) |
| Regional valuation factor | §256a SGB VI | Decreases continuously, 2025 = 1.0 (alignment reached) |
| Unemployment benefits accrue EP | §166 SGB VI para 1a | 80% × contribution ceiling / average earnings ≈ 1.5 EP/year |
| Additional-earnings limit (early pension) | §34 SGB VI | Fully abolished since 2023 |

### Tax (EStG — German income tax code) — typical blocks / options

| Anti-pattern | Paragraph | Effect |
|---|---|---|
| One-fifth rule severance | §34 para 1 EStG | Cheaper-option check against regular taxation — at high taxable income often no advantage |
| Progression clause | §32b EStG | Tax-free income (unemployment benefits, child allowance, foreign income) raises tax rate on other income |
| Loss-offset restriction capital assets | §20 para 6 EStG | Stock losses only against stock gains |
| Speculation period private | §23 EStG | 1 year for securities (abolished for stocks since 2009), 10 years for real estate |
| Advertising costs rental & lease | §9 EStG | Depreciation 2% (buildings), maintenance immediately, acquisition/production costs via depreciation |
| Taxable portion pension | §22 No. 1 EStG | Stepwise increase, 100% from pension start 2058 |
| Splitting tariff | §32a para 5 EStG | Only for married couples, joint assessment |

### Social insurance — typical blocks

| Block | Effect |
|---|---|
| Unemployment-benefit suspension | 12 weeks for own resignation without good reason (can be avoided via termination agreement, but risk clauses in agreement) |
| Severance suspension | if severance above certain limits → unemployment-benefit claim delayed by months |
| Contribution ceiling / insurance-mandatory limit | annually adjusted, affects health/care/pension/unemployment contributions |
| Assessment basis unemployment benefit | 80% of assessment earnings (capped by contribution ceiling) |

## Workflow

### Phase 1: Domain identification
- Which legal areas are affected? (e.g. pensions = SGB VI, taxes = EStG, unemployment = SGB III)
- Which person-specific constellations are relevant? (birth year, insurance status, contribution biography, family status)

### Phase 2: Anti-pattern catalog
- Load the matching cheat sheet above (or extend it)
- Explicitly ask the user about blocks that apply in their specific constellation
- Document in the code comment AND in the spec: which block is HOW modeled

### Phase 3: Positive rules (only now)
- Implement the calculation formulas
- Validate against the user's sheet / pension statement / tax assessment (control calculation)

### Phase 4: Transparency
- UI must show which blocks took effect (e.g. "7.2% deduction due to 45-year block" instead of just "gross pension XYZ")
- Unmet entitlement preconditions explicitly displayed

## Anti-patterns

- ❌ **Only modeling the positive entitlement conditions from Wikipedia/training** — you will miss the specific blocks
- ❌ **"Negligible" assumptions without user confirmation** — e.g. "unemployment benefits don't accrue EP" was wrong
- ❌ **Flat tax rate instead of real tariff** — flat is OK for quick estimate, but for decision apps the real §32a formula is needed
- ❌ **Assumption: all special provisions are included in standard calculation** — e.g. pension splitting, special supply, regional valuation
- ❌ **Modeling without paragraph reference** — code comment should contain the §-keyword so future iteration can find the rule
- ❌ **Pure calculation without entitlement-condition check** — user should see why which variant has which conditions

## Real-world impact

- **Pension-app session**: 3 substantial user corrections due to missing block consideration. Plan B-A was first modeled as "deduction-free" (WRONG), then with 7.2% deduction correctly (user pointed to §51 para 3a). Plan B-A → Plan B-B difference was corrected from 10k lifetime to 170k lifetime. Without this correction, the user would have built a wrong negotiation strategy.
- **Related patterns from earlier sessions**: brand-foundation origin question; multi-choice vs open-question (user style prefers open).
- **Lesson**: in domain modeling, the `ask the blocks first` discipline is the lever against 3-4 user corrections per session.
