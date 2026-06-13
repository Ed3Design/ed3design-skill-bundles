# schema-discipline

> SQL/Schema-Disziplinen die Bug-Klassen strukturell vermeiden.

## Skills (6)

| Skill | Verhindert |
|---|---|
| `schema-verify-via-information-schema` | „Wishful-Column"-Anti-Pattern: SELECT auf nicht-existente Spalten |
| `read-only-sql-via-regex-validator` | versehentliche UPDATE/DELETE in einem Read-Only-Pfad |
| `enum-known-values-via-insert-grep` | Stale Enum-Constants die echte DB-Werte nicht reflektieren |
| `enum-value-discovery-before-sql-where` | WHERE x = 'wrongValue' → silent empty result |
| `schema-use-case-mismatch-detection` | DB-Schema passt nicht zum Use-Case (z.B. NOT NULL wo NULL erwartet) |
| `explicit-unknown-counter-vs-coalesce-mask` | COALESCE versteckt NULL-Werte die als 0 gerendert werden |

## Komplementär zu

- `db-schema-inspector.py` Tool aus dem `token-savers`-Bundle — strukturierter Schema-Lookup als CLI-Tool

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/schema-discipline/skills"/* ~/.claude/skills/
```

## Lizenz

MIT. Empirik aus 4 Wochen Wolf-Trading-Platform-Schema-Drift-Cycles.
