# Technical Debt

Tracked items that are known and either addressed in the current release or scheduled for a defined follow-up.

## Skill description length — RESOLVED

**Status (2026-06-15, end-of-day)**: ✅ All 47 skill descriptions are now ≤ 1024 chars (Claude-Code spec recommendation). 27 over-length descriptions were trimmed from 1100–2389 chars to 797–1014 chars via per-skill semantic rewriting, preserving trigger-phrase coverage and the "do NOT load for…" guard rails.

The audit script `scripts/audit-skill-descriptions.py --check-length` now passes; CI enforces both `--check-first-person` (HARD) and the length check at the soft-warning level by default. Run with `--check` for combined hard-enforcement.

## Skill names with non-English words — RESOLVED

**Status (2026-06-15)**: ✅ The three German-named skills have been renamed to kebab-case English:

| Old name | New name |
|---|---|
| `silent-except-versteckt-schema-drift` | `silent-except-hides-schema-drift` |
| `forensik-hypothese-widerlegt-code-read-weiter` | `forensic-hypothesis-disproved-then-read-code` |
| `forensik-spur-fuer-fire-and-forget-sends` | `forensic-trail-for-fire-and-forget-sends` |

All cross-references in sibling skills, agents, README, and `marketplace.json` have been updated. No redirect-stubs were created because these skills had not yet been distributed via a stable marketplace cycle — the rename is therefore non-breaking.

## Test-fixture coverage for Python tools — RESOLVED

**Status (2026-06-15)**: ✅ The five tools (`vault-search.py`, `db-schema-inspector.py`, `diff-summary.py`, `html2md.py`, `img-preprocess.py`) now have CI smoke-tests covering `--help` exit-code + dependency-failure paths via `scripts/test-tools-smoke.sh`. Deeper unit-test coverage with mocked DB/SSH/Pillow inputs remains a separate follow-up — captured below.

### Follow-up: deeper unit-test coverage

The current smoke-tests verify command-line surface (help, missing-dep guards, basic option-parsing). Deeper behaviour-tests with mocked inputs (asserted scoring in vault-search, asserted JSON shape in diff-summary, asserted classification thresholds in img-preprocess) are scoped for a future test-scaffolding PR. Not a blocker for marketplace release.

## Cycle-2 polish backlogs per promoted skill

Every PROMOTED skill has a `## Background: TDD-Verlauf` (or equivalent) section with a Cycle-2-Backlog list of polish items from the GREEN-subagent self-reflection. These items are non-blocking and accumulate across releases. Worth a periodic batch-review pass.

## Maintained by

`maintainers@ed3works.com` — see `SECURITY.md` for the responsible-disclosure channel.
