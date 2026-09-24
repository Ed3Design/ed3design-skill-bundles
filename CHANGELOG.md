# Changelog

All notable changes to this repository are tracked here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) at the per-bundle level.

## [Unreleased]

### Added

- `validate-windows` CI job (`windows-latest`, Git Bash): runs the hook
  syntax check, hook trigger-matrix, tool smoke-tests and `py_compile` on
  Windows. Rationale: the bundle ships bash hooks and Python tools that users
  run under Git Bash, but CI was ubuntu-only, which made every
  Windows-portability claim in a PR structurally unverifiable. Scope is
  deliberately narrow — schema/counts/description audits are pure text
  analysis and stay ubuntu-only rather than being paid for twice.

- `scripts/audit-private-skill-crosslinks.py` + CI step: fails when a skill
  body references a back-ticked skill-name that resolves to neither a skill in
  this repo, a `superpowers:`/`gsd:` plugin, nor the curated allow-list (CSS
  props, libraries, CLI tools, sibling-bundle skills, built-ins). Catches the
  private-only dangling-reference class that `audit-stale-draft-crosslinks.py`
  (which only flags `-DRAFT` suffixes) misses.

- **9 skills published** (47 → 56), resolving dangling cross-references to skills that previously existed only in the private catalog: `asyncpg-live-vs-mock-shape` (async-forensik); `pre-migration-data-verification`, `production-seed-vs-demo-seed-split` (schema-discipline); `pre-deploy-code-drift-detection`, `external-advisor-output-plausibility-audit`, `mcp-server-stdio-to-http-migration`, `remote-script-scp-over-ssh-heredoc`, `frontend-ui-self-verify-before-user-demo` (code-quality); `docx-tab-position-extraction-for-layout-replication` (token-savers). Each was anonymized (real client/tenant names, private paths, hostnames, German body text removed), YAML-frontmatter-normalized, and trimmed to the ≤1024-char description spec. Counts regenerated across README, marketplace.json, all plugin.json, and bundle READMEs.
- `package.json` + `package-lock.json` so Dependabot can update the Claude Code CLI via PR (CI now uses `npm ci`)

### Fixed

- **All six warn-only hooks were silently ineffective** — fixed across
  `code-quality`, `skill-system-meta` and `token-savers`. Two independent causes,
  both reproduced rather than inferred:
  1. Every hook printed its warning to stderr and exited 0. The official hook
     documentation is explicit that this never reaches the model: *"Stderr from a
     hook that exits 0 goes to the debug log only, never the transcript, and Claude
     never sees it."* Each hook's own comment claimed the opposite. They now emit
     `hookSpecificOutput.additionalContext`, which is the documented channel, and
     `permissionDecision: "allow"` for the PreToolUse ones (that value does **not**
     bypass the permission system — the call still goes through the normal flow).
  2. Every hook invoked `python3` unconditionally to parse its stdin JSON. Where
     only `python` exists, the parse failed silently, the extracted command came
     back empty and the trigger was never evaluated. Resolved once per hook via
     `command -v python3 || command -v python`.
  Reproduction: in a PATH sandbox containing only `python`, `scripts/test-hooks.sh`
  scored **14 pass / 8 fail** before and **22 / 0** after; all eight failures were
  should-warn cases going silent. Unchanged on a normal Linux PATH (22 / 0 both ways).

- `scripts/test-hooks.sh` + `scripts/test-tools-smoke.sh` were not runnable on
  Windows: both assumed `python3` on PATH (Git Bash commonly has only
  `python`), and the smoke-test hardcoded `venv/bin/python3` where Windows
  venvs use `Scripts/` and ship no `python3` at all. Both now resolve the
  interpreter once and derive the venv layout from `uname -s`. In
  `test-hooks.sh` the old form was actively dangerous: a failed `python3`
  produced an empty payload, which the harness reads as "silent" — turning
  every should-warn case into a false PASS instead of a failure.

- **12 dangling cross-references** to private-only skills genericized to prose (a public user cannot install them): `communication-preferences`, `vault-decision-cross-file-sync`, `obsidian-vault-folder-restructure`, `obsidian-vault-graph-cleanup`, `tailscale-multi-account-diagnosis`, `traefik-internal-route-probe`. This finding class was previously uncaught because `audit-stale-draft-crosslinks.py` only flags `-DRAFT`-suffixed references, not references to skills absent from every public bundle.
- One residual private hostname (`botserver`) in `roadmap-phase-execution-verify-first` genericized to `your-server`.

- `scripts/test-tools-smoke.sh` behavioral block previously exited 0 even on FAIL — fixed with `[ "$FAIL" -gt 0 ] && exit 1` at the end. Verified via negative test: artificially-broken tool now produces exit 1
- `scripts/test-tools-smoke.sh` invoked tools via shebang while installing deps into `$TEST_PY` — fixed to call `"$TEST_PY" "$TOOLS_DIR/tool.py"` everywhere; dep installs use `"$TEST_PY" -m pip` not bare `pip`
- CI workflow now installs Pillow + beautifulsoup4 + certifi at job-setup (not just pyyaml). `STRICT_BEHAVIORAL=1` env-var makes missing-dep skips into HARD-fail in CI mode
- 2 dangling `-DRAFT` crosslinks to non-shipped sibling skills + 1 STUB-promotion-text leftover in a GA skill (`briefing-source-triangulation`) scrubbed
- `regenerate-counts.py` success message now reports `bundle plugin.json updated: <bundles>` when it rewrites them

## [0.2.0] — 2026-06-15

First stable marketplace release. Tagged at `487ec35` (post-PR #5 merge). Cumulative changes from PR #1 through PR #5:

- 35 broken YAML frontmatters fixed (block-scalar conversion)
- 6 DRAFT skills TDD-promoted to GA via real RED+GREEN subagent pressure-tests
- SQL-injection guard with regression test (`db-schema-inspector.py`)
- Privacy-redacted audit-log hook (`pre-push-bypass-audit.sh`)
- 27 over-length skill descriptions trimmed to ≤ 1024 chars
- 3 German-named skills renamed to English kebab-case
- 6-bundle structure: async-forensik, code-quality, planning-disciplines, schema-discipline, skill-system-meta, token-savers
- CI uses official `claude plugin validate --strict` per bundle (replaced regex re-implementation)

Sibling repository: [`ed3design-engineering-bundles`](https://github.com/Ed3Design/ed3design-engineering-bundles) for hardware/maker disciplines.

[Unreleased]: https://github.com/Ed3Design/ed3design-skill-bundles/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Ed3Design/ed3design-skill-bundles/releases/tag/v0.2.0
