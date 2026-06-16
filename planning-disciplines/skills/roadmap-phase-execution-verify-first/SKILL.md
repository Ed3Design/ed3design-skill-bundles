---
name: roadmap-phase-execution-verify-first
description: |-
  Captures a pattern from a Phase-A execution session: when executing a roadmap phase from a knowledge vault that was designed days/weeks ago AND a previous session may have prepared draft artifacts (service maps, status files, execution guides), verify each item against current reality (DB queries, docker inspect, systemctl, filesystem) BEFORE applying changes. Find drift in pre-existing files; document discoveries that turn a routine item into an issue; never check a roadmap item as done just because the roadmap said so. Trigger on phrases like "implement Phase X", "execute roadmap item", "implement Phase A of … consolidation", "item Y from the roadmap", "execute the phase from the vault". Do NOT load for fresh roadmap design (use brain-dump-to-phased-roadmap), for executing a freshly-written task list with no vault history, or for non-vault roadmaps.
---

# Roadmap-Phase-Execution: Verify-Before-Touch

> ✅ **PROMOTED**: TDD pressure test passed. RED subagent showed a reasonable verify-first proposal (scan daily notes, DB query, Pi status). GREEN subagent went one step further: read the EXISTING Phase-A roadmap in the vault and discovered **Phase A is already completed** (audit log + commit hashes present) → drift table shown, 3-scenarios sanity question instead of check-mark setting, Phase 3 (execution) explicitly not started. Skill prevented false-positive "done" setting. Cycle-2 backlog: fallback-mode no-SSH-subagent, "phase already done" anti-pattern line, trust-boundary check.

## Overview

When executing a roadmap phase from a knowledge vault (Phase A/B/C of a consolidation roadmap, or similar multi-item phases) the default reaction "check off item by item" is dangerous. Three sources of silent drift:

1. **The roadmap itself** was written days/weeks earlier and contains statements that no longer hold (e.g. "3 open trades" — today 15)
2. **Prior sessions have already prepared artifacts** (service map, status files, execution guides) — often with remembered values instead of measurements
3. **Items may already be factually done** (e.g. "disable Pi services" — Pi was already clean), but tied to the condition "X confirmed" which itself does not hold

**Core principle**: verify each item against reality first, then execute the right action — which can be "update", "verify-only", "discovery-doc instead of check-mark" or "original-action".

## When to use

Trigger phrases:
- "Implement Phase A/B/C of …"
- "Execute roadmap item"
- "Execute the phase from the vault"
- "Item Y from the roadmap"
- "Implement roadmap … X"

Concrete signals:
- Roadmap file lives in `Projects/.../Roadmap-*.md` with items A1-A6 / B1-B5 etc.
- Roadmap date is > 3 days old
- In the same folder there are already artifacts like `*-Service-Map.md`, `*-status.md`, `*-Execution-Guide.md`
- User trigger is "implement Phase X", not "design Phase X fresh"

## When NOT to use

- **Fresh roadmap design**: consolidate brain-dump into roadmap → `brain-dump-to-phased-roadmap`
- **Freshly-written task list** (same day, same session, no prior artifacts): just work through, no verify overhead needed
- **Non-vault roadmap**: if the source is GitHub Issues, Linear, Jira or another tool, not the personal vault, different drift patterns apply (there primarily `gsd:gsd-execute-phase` or similar triggers)

## The 3-phase loop

### Phase 1 — Reality inventory (before the first edit)

Before any file is touched, invest a few minutes in verification queries:

| What the roadmap claims | Where to verify it |
|---|---|
| Containers/services run on host X | `ssh user@host "docker ps"` + `systemctl list-timers --all` |
| Database has N rows / trades / records | `docker exec <db> psql -U <user> -d <db> -c "SELECT count(*)..."` |
| Hardware inventory (CPU, RAM, disk, cores) | `ssh user@host "nproc && free -m && df -BG /"` |
| Another machine is warm-standby/disabled | `ssh user@other-host "systemctl list-units --state=enabled \| grep ..."` |
| Backup coverage exists | `cat /etc/<backup-tool>/conf.d/*.sh` + `ls <backup-staging-dir>/` + snapshot list |
| Prior status file is current | Compare file content vs. above reality sources |

**Output of this phase**: a small "drift table" — roadmap claim vs. reality, in bullet form. This table is the decision basis for everything that follows.

### Phase 2 — Sequencing & sanity-check with the user

Before starting to write:

1. **Show the drift table to the user** (especially if 2+ items are drift-affected)
2. **Propose sequencing**: first document (drift repair) → then verify → then change
3. **Clarify scope questions** if a roadmap assumption was wrong (e.g. "roadmap says 3 trades, DB says 15 — document all 15 or stay with 3 with a note?")
4. **Clarify depth questions** if an item contains destructive actions (e.g. "A2 says 'disable Telegram-Send' — verify only, env-flag-guard, or code refactor?")

**Output of this phase**: user-confirmed sequence + scope + depth for each item.

### Phase 3 — Execution with discovery mandate

Per item:

1. **Reality check for this specific item** (DB / docker / SSH / filesystem)
2. **If item no longer applies** (e.g. "disable services" — services already disabled):
   - DO NOT dutifully write "✓"
   - Instead: document discovery ("verified: services already disabled" + new issue if verify itself reveals something, e.g. "backup missing")
3. **If item updates a prior artifact**: NOT edit-on-top, but reality comparison → if drift > 30% → complete rewrite with verified values
4. **If item is a code change**: follow the usual TDD/smoke-test loop (a framework-specific deploy-iteration workflow if you have one, otherwise project-specific)
5. **Interim review** with user before next item

## Anti-patterns

| Anti-pattern | What to do instead |
|---|---|
| "Roadmap item A5 says 'X disable + Y confirm' → I check both off" | Verify-first: is X already disabled? Is Y really confirmed? Discovery-doc on discrepancy |
| Extend prior service map without reality check | Reality comparison + complete rewrite if drift > 30% |
| "The prior session was 'done' with the item, I don't have to do anything" | Prior `done` markings are not verification; measure yourself |
| Bury discovery issues in one file | Multi-file anchor — record the discovery consistently across every file that states it (hardware inventory + service map + repo-CLAUDE.md) |
| Backup confirmation as mandatory check without test | Concrete test snippet: `ls <backup-staging-dir>/` + `<backup-tool> snapshots --json` + container filter logic check |

## Quick-Reference Reality-Check Commands (typical stack)

```bash
# Container status on your-server
ssh user@your-server "docker ps --filter name=<stack>"

# DB content (derive user+DB name from container env!)
ssh user@your-server "docker inspect <db-container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES"
ssh user@your-server "docker exec <db-container> psql -U <user> -d <db> -c '\dt'"

# Host timer + systemd status
ssh user@your-server "systemctl list-timers --all | grep -v restic-system"

# host sanity (decommission check)
ssh user@your-server "crontab -l | grep -v '^#' ; systemctl --user list-unit-files --state=enabled"

# Backup coverage (e.g. Restic + pre-hooks)
ssh user@your-server "cat <backup-config-path>/backup.sh ; ls -la <backup-staging-dir>/"
```

## Real-world impact

Phase-A consolidation session of `your-app` (6 items A1-A6):

- **A1 Service Map**: Prior file said "DB user `postgres`, DB name `production`, 11 hypertables, port 5433 external". Reality: different user/db/7 hypertables/no host-port mapping. Edit-on-top would have left it wrong — complete rewrite with verified values was right.

- **A4 v3-trades-open**: Prior file said "3 open trades #1, #3, #4" with entry prices that differed from DB by 30%. Reality: 15 open trades (IDs 1, 3-16). User scope question clarified → all 15 documented with correct entry/stop/leverage values.

- **A5 Decommission of old host**: Roadmap said "disable services, confirm backup". Reality: services were already disabled — but backup was NOT confirmed. `pre-backup-hooks/postgres-dumpall.sh` did not match the container name, the backup tool excluded `<docker-data-dir>/**`, and `<backup-staging-dir>/` was empty. Without verify-first discipline, "backup confirmed ✓" would have been the most dangerous false-positive of the session.

- **A6 Repo-CLAUDE.md**: Updating the Pi-centric file without reality comparison would have left the Pi stack inventory in the "production environment" table. Reality-first: table completely switched to the new server, old Pi commands marked as "HISTORICAL for backup recovery".

**Result**: 30% of session time went into drift repair, 70% into real implementation — and a latent dangerous backup issue was uncovered that would have stayed dormant without the verify-first pattern.

## Cross-References

- `superpowers:writing-skills` — TDD-iron-law protocol for skill creation
- Cross-file decision-sync discipline — keep a discovered fact consistent across every file that states it (don't fix it in one place and leave drift elsewhere)
- `brain-dump-to-phased-roadmap` — predecessor step (roadmap design) supplying this skill with material
- Maxim "Current Truth before Timeline" — the mindset foundation
- Maxim "In construction, measure, never estimate" — the engineering root of the pattern

## Background: TDD log (Bulletproofing log)

### Cycle 1 (PASS — with surprising GREEN behavior)

- **RED subagent** (without skill, Phase-A execution task): Sensible answer (b) reality-check first. Cited CLAUDE.md maxims directly ("first read logs/code/DB", "avoid closed-as-done"). Proposed concrete reality-check order (scan daily notes, git log, live trades, Pi status, service-map comparison). Very close to GREEN behavior — RED is also clever here.
- **GREEN subagent** (with skill, same prompt): Went beyond RED — **read the existing roadmap file in the vault** and discovered: Phase A is already marked as ✅ DONE with full audit log (commits and snapshot present). Built drift table against the user instruction. Asked 3-scenarios sanity question (test? check-mark catch-up? rollback?). **No check-mark set, no file edited** — Phase 3 (execution) gated until user answers.
- **Verdict**: GREEN clearly superior — avoided false-positive "check-mark by check-mark" execution although phase was already done. RED would probably have gotten stuck in Phase 1 (reality check) without opening the roadmap itself.

### Cycle-2 backlog (polish, non-blocking)

1. **Fallback mode for no-SSH-tool subagent** documented (vault as reality proxy + audit-log cross-reference + explicit command listing) — as the GREEN subagent substituted today
2. **Anti-pattern line** added: "Phase already done → skill output is drift report, NOT check-mark catch-up without reality check"
3. **Trust-boundary check section**: what to do on contradiction between user instruction and vault audit log? Sanity question BEFORE edit, no auto-resolve.
4. **Skill composition hint**: needs communication-style guidance (sanity-question tonality) + a cross-file decision-sync discipline (multi-file discovery anchoring)
