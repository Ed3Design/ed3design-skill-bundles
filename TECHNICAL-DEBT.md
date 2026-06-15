# Technical Debt

Tracked items that are intentionally NOT fixed in the current release but are known and will be addressed in follow-up PRs.

## Skill description length (soft spec violation)

**Status**: 27 of 47 skills (as of 2026-06-15 audit) have a `description` field longer than the Claude-Code skill-spec recommendation of **1024 chars**. The validator does not enforce this — but very long descriptions:

- bloat the system prompt every time the skill metadata loads,
- degrade trigger-match precision (more keywords = noisier match signal),
- violate the writing-skills meta-skill recommendation of "under 500 if possible".

### Why not fix in this PR

Each description is **semantic content** — fixing requires per-skill rewriting that preserves the trigger-phrase coverage, the "do NOT load for" guard rails, and the failure-mode-encoding without losing the skill's discoverability. A mechanical mass-trim would risk over-trimming the trigger-language that makes the skill load at the right moment.

### Plan

- A follow-up PR will go skill-by-skill (or skill-cluster-by-cluster), with per-skill commits.
- Target: every description ≤ 800 chars (comfortably under the 1024 spec recommendation, leaving headroom for cycle-2 expansions).
- Test plan: each rewrite is verified by (a) `claude plugin validate --strict`, (b) a Red+Green subagent pair using the new description to confirm trigger-coverage hasn't regressed.

### Current top-10 worst

(See `scripts/audit-skill-descriptions.py` for live counts.)

| Length | Skill |
|---:|---|
| 2055 | schema-discipline/enum-known-values-via-insert-grep |
| 2022 | code-quality/silent-except-versteckt-schema-drift |
| 2020 | code-quality/cross-file-source-of-truth-grep |
| 1915 | planning-disciplines/strategic-proposal-vault-persistence-check |
| 1801 | code-quality/aggregate-code-review-after-tdd-tasks |
| 1789 | async-forensik/reporting-artefact-detection-before-claiming-anomaly |
| 1785 | code-quality/subprocess-ssh-arg-quoting-via-shlex |
| 1721 | async-forensik/async-context-manager-retry-pattern |
| 1691 | code-quality/static-source-bug-class-coverage-test |
| 1670 | async-forensik/asyncio-fire-and-forget-loop-exit-await |

## Skill names with non-English words

**Status**: 3 skills carry German loanwords in the name:

- `async-forensik/forensik-hypothese-widerlegt-code-read-weiter`
- `async-forensik/forensik-spur-fuer-fire-and-forget-sends`
- `code-quality/silent-except-versteckt-schema-drift`

These work but reduce discoverability for English-only users and break the kebab-case English convention of the rest of the catalog.

### Plan

- Rename to English kebab-case in a follow-up PR.
- Provide **redirect stubs** at the old paths for one minor-version cycle (skill files that contain only a "moved to X" notice + the new full content under the new name) so existing user-installations don't silently break auto-discovery.
- Update all cross-references in other skills.

## Cycle-2 polish backlogs per promoted skill

Every PROMOTED skill has a `## Background: TDD-Verlauf` (or equivalent) section with a Cycle-2-Backlog list of polish items from the GREEN-subagent self-reflection. These items are non-blocking and accumulate across releases. Worth a periodic batch-review pass.

## Test-fixture coverage for Python tools

5 tools have `argparse` but no self-test invocations (`--self-test`, doctest, or unit tests). Currently we rely on `python -m py_compile` + manual smoke-tests. A modest test suite (e.g. `pytest tests/tools/`) would catch regressions in tool behaviour before they reach users.

## Maintained by

`maintainers@ed3works.com` — see `SECURITY.md` for the responsible-disclosure channel.
