# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this skill-bundle repository — whether in:

- a **Python tool** (`*/tools/*.py`) that could be exploited at runtime,
- a **shell hook** (`*/hooks/*.sh`) that could be tricked into unsafe behavior,
- a **skill description** that, if loaded, would steer Claude towards an unsafe pattern,
- a **CI workflow** (`.github/workflows/*.yml`) that could be exploited via PR-injection,

please **do not open a public GitHub issue**. Instead, report it privately:

- Email: open a [GitHub Security Advisory](https://github.com/Ed3Design/ed3design-skill-bundles/security/advisories/new) — this opens a private channel between you and the maintainers.

We will:

1. Acknowledge receipt within 5 business days.
2. Investigate and provide an initial severity assessment within 10 business days.
3. Coordinate disclosure: agree on a fix timeline and credit you publicly once the fix is released (or anonymously if you prefer).

## In Scope

- SQL injection, shell injection, path traversal, SSRF, or arbitrary code execution in the bundled Python tools.
- Skills that, if loaded by Claude, would systematically suggest unsafe operations against the user's machine (deleting unrelated files, exfiltrating credentials, running untrusted code without consent).
- Hooks that leak secrets (commands, tokens, credentials) into logs or external services.
- CI workflows vulnerable to untrusted-input-injection (`github.event.*` interpolation, malicious `ref:` parameters).

## Out of Scope

- Bugs in third-party dependencies (Pillow, BeautifulSoup, certifi) — report those upstream.
- Issues in Claude Code itself or in the `claude` CLI — report to Anthropic.
- Theoretical attacks requiring an already-compromised local machine.
- Social-engineering scenarios where a user voluntarily installs a malicious sibling bundle.

## Supported Versions

This repository follows semantic versioning at the bundle level. Security fixes are backported to the previous minor version (`v0.N.X` series) for 90 days after a new minor release.

## History

| Date | CVE / Advisory | Affected | Fixed in |
|---|---|---|---|
| (none yet) | — | — | — |
