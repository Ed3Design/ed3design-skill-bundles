# async-forensik

> Forensic disciplines for asyncio Python + container stacks. Hard-won debugging lessons as skills.

## Skills (8)

| Skill | Pain Point |
|---|---|
| `db-telemetry-primary-docker-logs-secondary` | Docker logs rotate on high volume → DB telemetry as primary source |
| `forensic-hypothesis-disproved-then-read-code` | 3 hypotheses disproved ≠ no bug — bonus findings emerge during disproof |
| `forensic-trail-for-fire-and-forget-sends` | asyncio fire-and-forget double-sends are perception loops |
| `reporting-artefact-detection-before-claiming-anomaly` | 3-filter triage (NULL/cross-window/methodology) before forensic dispatch |
| `async-context-manager-retry-pattern` | Retry pattern for async with blocks |
| `asyncio-fire-and-forget-loop-exit-await` | Loop exit not awaited → tasks dangling |
| `ephemeral-container-file-detection` | File exists in container but `docker exec` doesn't see it (tmpfs/overlay) |
| `asyncpg-live-vs-mock-shape` | asyncpg type coercion (Decimal/str/UUID/INET) → mock-vs-live divergence in tests |

## 🤖 Sub-Agent (1)

| Agent | Description |
|---|---|
| `forensik-detective` | Hypothesis-test pipeline (H1/H2/H3) + DB-telemetry-primary > docker-logs-secondary + bonus-finding detection after disproof. Prevents "no bug = false alarm" wrong-closures. Sonnet model |

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/async-forensik/skills"/* ~/.claude/skills/
```

## Trigger Domain

Applies to any asyncio Python stack with Docker Compose. Anti-pattern detection before unnecessary forensic loops.

## License

MIT.
