# Changelog

All notable changes to this repository are tracked here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) at the per-bundle level.

## [Unreleased]

### Added

- **9 skills published** (47 → 56), resolving dangling cross-references to skills that previously existed only in the private catalog: `asyncpg-live-vs-mock-shape` (async-forensik); `pre-migration-data-verification`, `production-seed-vs-demo-seed-split` (schema-discipline); `pre-deploy-code-drift-detection`, `external-advisor-output-plausibility-audit`, `mcp-server-stdio-to-http-migration`, `remote-script-scp-over-ssh-heredoc`, `frontend-ui-self-verify-before-user-demo` (code-quality); `docx-tab-position-extraction-for-layout-replication` (token-savers). Each was anonymized (real client/tenant names, private paths, hostnames, German body text removed), YAML-frontmatter-normalized, and trimmed to the ≤1024-char description spec. Counts regenerated across README, marketplace.json, all plugin.json, and bundle READMEs.
- `package.json` + `package-lock.json` so Dependabot can update the Claude Code CLI via PR (CI now uses `npm ci`)

### Fixed

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
