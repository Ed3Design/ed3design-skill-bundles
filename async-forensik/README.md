# async-forensik

> Forensik-Disziplinen für asyncio-Python + Container-Stacks. Hard-won Debugging-Lehren als Skills.

## Skills (7)

| Skill | Pain-Point |
|---|---|
| `db-telemetry-primary-docker-logs-secondary` | Docker-Logs rotieren bei high-volume → DB-Telemetry als Primärquelle |
| `forensik-hypothese-widerlegt-code-read-weiter` | 3 Hypothesen widerlegt ≠ kein Bug — Bonus-Findings entstehen beim Disproof |
| `forensik-spur-fuer-fire-and-forget-sends` | asyncio Fire-and-Forget-Doppel-Sends sind Wahrnehmungs-Loops |
| `reporting-artefact-detection-before-claiming-anomaly` | 3-Filter-Triage (NULL/Cross-Window/Methodik) vor Forensik-Dispatch |
| `async-context-manager-retry-pattern` | Retry-Pattern für async with-Blocks |
| `asyncio-fire-and-forget-loop-exit-await` | Loop-Exit nicht awaitet → Tasks dangling |
| `ephemeral-container-file-detection` | File im Container existiert, aber `docker exec` sieht es nicht (tmpfs/overlay) |

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/async-forensik/skills"/* ~/.claude/skills/
```

## Trigger-Domain

Greift bei jedem asyncio-Python-Stack mit Docker-Compose. Anti-Pattern-Detection vor unnötigen Forensik-Loops.

## Lizenz

MIT.
