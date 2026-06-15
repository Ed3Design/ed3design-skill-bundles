# Changelog

All notable changes to this repository are tracked here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) at the per-bundle level.

## [Unreleased]

### Added

- Behavioral smoke-tests for all token-savers tools (real subcommand invocations against fixtures, not just `--help`)
- `scripts/audit-stale-draft-crosslinks.py` — CI gate that fails if any skill body references `<name>-DRAFT` while a GA `<name>` exists
- `regenerate-counts.py` now also validates and rewrites per-bundle `.claude-plugin/plugin.json` descriptions
- `CHANGELOG.md`, `.github/dependabot.yml`, `.github/CODEOWNERS`
- CI Actions pinned to commit-SHAs; Claude Code CLI pinned to a specific version

### Fixed

- `token-savers/tools/img-preprocess.py` `colors` subcommand crashed with `NameError: name 'Image' is not defined` because the lazy Pillow import was missing for this entry point
- Stale `-DRAFT` cross-references removed from 7 skill bodies (8 references) that were left over after the GA promotion
- `token-savers/.claude-plugin/plugin.json` description claimed "4 skills" — corrected to 3
- `SECURITY.md` wording: "Email" bullet label was inconsistent with its GitHub Security Advisory content

## [0.2.0] — 2026-06-15

Initial public marketplace release after a four-PR audit-and-fix cycle:

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
