---
name: Skill proposal
about: Suggest a new skill for an existing bundle (or a new bundle)
title: "[skill] <bundle>: <skill-name-kebab>"
labels: skill-proposal
assignees: ''
---

## ABC criterion check (please pre-fill)

The repository only accepts skills that pass all three filters from `skill-system-meta`:

- **A — Repeatable pattern with clear steps?**
  (Does the skill resolve to ≥3 concrete numbered actions? Or is it a vague principle that belongs in a memory entry instead?)
- **B — Without the skill, would Claude reliably get it wrong?**
  (Have you observed the wrong-path-then-correction loop? A 5-minute write-up should save a future 2-hour re-discovery.)
- **C — Transferable beyond a single project?**
  (Does the pattern apply to >1 project / >1 domain? Project-specific stays in CLAUDE.md.)

If the answer to any of A/B/C is "no," the right home is likely a memory entry or project CLAUDE.md — not a public skill.

## Proposed name + bundle

- Name: `<skill-name-kebab>`
- Target bundle: `<bundle-name>` (or "new bundle: <suggested-name>")

## Trigger phrases (verbatim)

What would the user be saying that should load this skill?

## Anti-pattern this prevents

What's the natural wrong default that Claude takes without the skill? Be specific — paste a RED-baseline observation if you have one.

## Compatible / conflicting skills

Are there existing skills (in this repo or `superpowers:`) that overlap or conflict? How does this differ?

## TDD-promotion status

- [ ] Pattern observed in ≥2 sessions
- [ ] RED-test outcome documented (what Claude does without the skill)
- [ ] GREEN-test outcome documented (what Claude does with the skill)
- [ ] Ready for review

If any boxes are unchecked, this is a DRAFT proposal and may be filed under "needs-tdd-cycle" until validated.
