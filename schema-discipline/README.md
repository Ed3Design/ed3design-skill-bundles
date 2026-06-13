# schema-discipline

> SQL/schema disciplines that structurally avoid bug classes.

## Skills (6)

| Skill | Prevents |
|---|---|
| `schema-verify-via-information-schema` | "Wishful-column" anti-pattern: SELECT on non-existent columns |
| `read-only-sql-via-regex-validator` | Accidental UPDATE/DELETE on a read-only path |
| `enum-known-values-via-insert-grep` | Stale enum constants that don't reflect real DB values |
| `enum-value-discovery-before-sql-where` | WHERE x = 'wrongValue' → silent empty result |
| `schema-use-case-mismatch-detection` | DB schema doesn't fit the use case (e.g. NOT NULL where NULL is expected) |
| `explicit-unknown-counter-vs-coalesce-mask` | COALESCE hides NULL values rendered as 0 |

## 🤖 Sub-Agent (1)

| Agent | Description |
|---|---|
| `schema-validator` | Read-only sub-agent. Cross-checks code SQL refs (SELECT/INSERT/UPDATE/WHERE) against `information_schema` ground truth. Detects wishful-column / silent-empty-result / NULL-on-NOT-NULL / dead-column / stale-enum-constant drift. Sonnet model |

## Complementary to

- `db-schema-inspector.py` tool from the `token-savers` bundle — structured schema lookup as CLI tool

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/schema-discipline/skills"/* ~/.claude/skills/
```

## License

MIT. Empirical patterns from sustained schema-drift cycle experience.
