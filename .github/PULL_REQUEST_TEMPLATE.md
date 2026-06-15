<!--
Thanks for the PR. Quick checklist before maintainers spend cycles on review:
-->

## Summary

(1-3 sentences. What changes, and what it gives the user.)

## Type

- [ ] Bug fix (mechanical, doesn't change skill / tool semantics)
- [ ] New skill (DRAFT or promoted via TDD-cycle — see below)
- [ ] Existing skill expansion (add capability — requires `ga-skill-edit-tdd-workflow`)
- [ ] Tool / hook change
- [ ] Repo / CI / docs

## Validator + tests (run locally before pushing)

- [ ] `claude plugin validate --strict <bundle>` passes for every touched bundle
- [ ] `python3 scripts/regenerate-counts.py --check` passes (no drift)
- [ ] `python3 scripts/test-sql-injection-guard.py` passes (if you touched `db-schema-inspector.py`)
- [ ] `bash scripts/test-hooks.sh` passes (if you touched a hook)

## For new-skill PRs

- [ ] ABC-pass evidence: which concrete failure mode does the skill prevent, and what RED+GREEN evidence supports that?
- [ ] Description is **third-person** (no "I/we/my/our") and ideally <500 chars
- [ ] No `⚠️ DRAFT` banner if marked promoted; PROMOTED banner with date + Cycle-1 evidence if so
- [ ] `## Background: TDD-Verlauf` section appended for promoted skills

## For expanded / renamed skills

- [ ] Applied `code-quality/skills/ga-skill-edit-tdd-workflow` workflow (Pre-Step-0 + DRAFT-staging + RED+GREEN for the NEW capability only)
- [ ] Cycle-2 entry appended to TDD-Verlauf section
- [ ] Trigger-phrase coverage for the OLD class preserved in the new description (if rename)

## Sensitive content

- [ ] No real server paths (`/srv/...`, `/Users/<your-name>/...`) in skill bodies — use `~/projects/...` or `<your-server>` placeholders
- [ ] No real container names, IPs, tokens, or org-specific identifiers
- [ ] No personal names or session-narrative residue

🤖 PRs generated with `claude` will be reviewed at the same bar as human PRs.
