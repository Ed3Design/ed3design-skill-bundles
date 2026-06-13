---
name: bash-output-filtering-disciplines
description: Use BEFORE running any Bash command that could produce more than ~50 lines of stdout: `docker logs`, `docker ps -a` (long format), `git log` (full history), `find` (deep tree), `ps aux`, `psql -c "SELECT * FROM ..."`, `cat large.log`, `ls -la` (deep dirs), `journalctl`, `dmesg`, `kubectl logs`, `du -a`. STOP and apply head/tail/grep/wc/jq/awk/sed pre-filters in the SAME command pipeline — never let raw output flow into the conversation context. Every line above the relevant data is wasted tokens that accumulate over a session (~50k tokens for container status alone in a single morning). Trigger phrases like "docker logs container X", "look at git log", "find files with pattern", "ps aux", "journalctl", "SELECT * FROM table", "search complete logs", "what's in the directory", "ls on a large folder", "why is my session token usage so high". Do NOT apply when the user EXPLICITLY asked for full output ("show me the complete output", "please unfiltered"), for commands that are inherently small (`whoami`, `pwd`, `uname -a`, `date`), for one-shot value-extractions (`echo $VAR`, `grep -m1 PATTERN file`), or when piping to a file (`cmd > /tmp/full.txt` — file-write is fine, follow-up Read can be filtered). Encodes token-optimization pain: a morning session can easily burn ~30k tokens just on Bash tool outputs (cockpit + docker ps + docker logs without tail).

---

# Bash Output Filtering Disciplines

> ✅ **PROMOTED** via TDD-Cycle. RED-Subagent self-reflected "my default is clearly not token-efficient — 50× more tokens than necessary". GREEN-Subagent achieved with skill **~98% saving** (~500 tokens instead of ~50k) via 1 SSH call with server-side for-loop instead of 5× sequential SSH calls.

## Overview

**Pain anchor**: a single health-check sweep can burn ~15-20k tokens purely through unfiltered Bash outputs (container lists, logs without tail, SELECT * instead of count, find without head). Over 30 production-domain sessions/month ≈ ~500k tokens of pure boilerplate.

**Core discipline**: Filter **in the same command pipeline**, not "I'll filter mentally after reading". Once output is in the conversation context, the tokens are spent — whether you read it or not.

## When to Trigger

✅ **YES — filter first:**
- Command could produce > 50 output lines
- Command has `*` wildcard or tree recursion (`find /`, `ls -laR`)
- DB query without `LIMIT`, `count(*)` or `EXPLAIN`
- Log reading without `--tail` / `--since`
- Process listing without `grep PROCESS_NAME`
- File listing in unknown (potentially large) directory

❌ **NO — fully OK:**
- User explicitly said "complete output please"
- One-shot value-extract (`whoami`, `date`, `pwd`, `echo $VAR`)
- Tool output is known-small (< 50 lines guaranteed)
- Pipe-to-file for later (`cmd > /tmp/x.txt` → Read with `offset+limit` afterwards)

## Pattern Catalog

### 1. `docker logs` — ALWAYS with `--tail` OR `--since`

```bash
# ❌ bad: all logs since container start
docker logs your-app

# ✅ good: last 50 lines
docker logs --tail 50 your-app

# ✅ better: time-bounded
docker logs --since 30m your-app

# ✅ best: + grep for relevant
docker logs --since 1h your-app 2>&1 | grep -iE "error|warning" | tail -20
```

### 2. `docker ps` — Restrict format

```bash
# ❌ bad: full format with lots of whitespace
docker ps -a

# ✅ good: only name + status
docker ps --format "table {{.Names}}\t{{.Status}}"

# ✅ better for 1-line health check:
docker ps --format "{{.Names}}: {{.Status}}" | grep -v healthy
# → shows ONLY unhealthy/restarting containers
```

### 3. `git log` — ALWAYS with `-n N` or `--oneline`

```bash
# ❌ bad: full history with full format
git log

# ✅ good: last 10 commits one-line
git log --oneline -n 10

# ✅ better: only SHA + subject + date
git log --pretty=format:"%h %ad %s" --date=short -n 20
```

### 4. `find` — ALWAYS with output cap

```bash
# ❌ bad: can dump thousands of files
find /path/to/projects -name "*.py"

# ✅ good: max 20 files
find /path/to/projects -name "*.py" | head -20

# ✅ better: count only
find /path/to/projects -name "*.py" | wc -l

# ✅ best: use Glob tool for vault/repo searches (token-cheaper than find+pipe)
```

### 5. `psql` — `LIMIT`, `count(*)`, `--csv`

```bash
# ❌ bad: could return 10,000 rows
psql -c "SELECT * FROM trades"

# ✅ good: LIMIT + relevant columns
psql -c "SELECT id, symbol, status FROM trades ORDER BY id DESC LIMIT 10"

# ✅ better: aggregate instead of rows
psql -c "SELECT count(*), status FROM trades GROUP BY status"

# ✅ output format for subagent processing
psql --csv -c "SELECT id, symbol FROM trades LIMIT 10"
```

### 6. `ps aux` — ALWAYS with `grep`

```bash
# ❌ bad: all processes on the system
ps aux

# ✅ good: only the process of interest
ps aux | grep -i python | grep -v grep | head -5
```

### 7. `journalctl` / `dmesg` — Time filter

```bash
# ❌ bad: all boot logs
journalctl

# ✅ good: only last hour, errors only
journalctl --since "1 hour ago" -p err --no-pager | tail -50
```

### 8. `cat large.log` / Full-file read

```bash
# ❌ bad: dumps complete log file into context
cat /var/log/app.log

# ✅ good: end only
tail -100 /var/log/app.log

# ✅ better: only relevant lines
tail -1000 /var/log/app.log | grep -iE "error|critical"

# ✅ for Read tool: use offset + limit
# Read file_path="/var/log/app.log" offset=5000 limit=200
```

### 9. JSON output — `jq -c` for one-line

```bash
# ❌ bad: pretty-printed JSON with every line expanded
curl http://api/data

# ✅ good: compact one-line per object
curl -s http://api/data | jq -c '.[]' | head -20

# ✅ better: only relevant fields
curl -s http://api/data | jq -c '.[] | {id, status}' | head -20
```

### 10. `ls -la` on large folders

```bash
# ❌ bad: everything
ls -la ~/.claude/skills/

# ✅ good: only directory count
ls ~/.claude/skills/ | wc -l

# ✅ better: names in one column
ls ~/.claude/skills/ | head -20
```

### 11. `du -sh` instead of `du -a`

```bash
# ❌ bad: every file individually
du -a ~/Downloads

# ✅ good: only summary
du -sh ~/Downloads

# ✅ top-10 largest dirs
du -sh ~/Downloads/* | sort -rh | head -10
```

### 12. `wc -l` as preliminary probe

When it's unclear whether output is large:

```bash
# Probe first (one integer output)
cmd | wc -l
# → if < 50: cmd without filter
# → if > 50: add filter
```

## Heuristic: Which filter when

| Output type | Default filter | Reasoning |
|---|---|---|
| Logs (temporal) | `--tail 50` or `--since 30m` | Recent is usually more relevant than history |
| Logs (pattern) | `grep -iE "error\|warn" \| tail -20` | Pre-filter ERROR class |
| Lists (files, containers, processes) | `\| head -20` | Sample is enough for overview |
| Lists (count requested) | `\| wc -l` | Just the number |
| Tables (DB) | `LIMIT 10` or `count(*)` | Full dumps are rarely productive |
| JSON streams | `jq -c '.field' \| head -20` | Compact + relevant |
| Find/Search | `\| head -20` | First hits suffice, otherwise refine pattern |

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| `cmd > /tmp/x.txt && cat /tmp/x.txt` | File-write OK, then `Read offset+limit` or `tail/head` directly |
| Re-run the same command "because I want to see it again" | Output is in history — recall, don't re-run |
| `docker logs container \| less` | `less` does nothing for token context (no interactive reader in Bash tool) |
| `find / -name "X"` without cap | ALWAYS `\| head`, or better, Glob tool |
| `psql -c "SELECT *"` | `LIMIT` or `count` — otherwise memory + token burn |
| Relying on user-confirm "okay, can you show the last 10?" | Pre-filter, then optionally "more on request" note |
| Five SSH+docker exec calls instead of 1 HTTP-aggregator call | If MCP/health-aggregator exists: use it instead of SSH chain |
| Output `2>&1` without stderr need | Only merge stderr when you want to read errors along |

## Cost-of-Skipping

Empirical from work sessions (estimated):

| Operation | Without skill (typical) | With skill | Saving |
|---|---|---|---|
| Container health-check (5 containers) | ~3-5k (`docker ps -a` + 5× `docker inspect`) | ~200 (`docker ps --format "..."`) | **~95%** |
| Recent error sweep | ~5-8k (`docker logs` unfiltered × N containers) | ~500-800 (`docker logs --since 30m \| grep ERROR \| tail -20`) | **~90%** |
| Git log review per repo | ~2-3k | ~200 (`git log --oneline -n 10`) | **~93%** |
| Find search in large tree | ~3-10k | ~300 (`\| head -20` or Glob tool) | **~95%** |
| DB trade statistics | ~800-2000 (`SELECT *`) | ~50-100 (`count(*)`) | **~95%** |

**Projection**: 30 sessions/month × 3-5 of these operations per session × 5k saved = **~450-750k tokens/month structurally avoided**.

## Connection to other Skills

- **`db-telemetry-primary-docker-logs-secondary`** (GA): That skill preaches DB telemetry **instead of** Docker logs as primary. This skill is the complementary discipline **when** Docker logs are needed (secondary).
- **Sub-agent model matrix**: bulk smoketest subagents use Haiku — if Bash output stays large, the token cost per subagent multiplies. Filter discipline reduces subagent cost too.
- **`reporting-artefact-detection-before-claiming-anomaly`** (GA): before claiming an anomaly, check whether the Bash output sample was large enough (anti-pattern: deriving an anomaly from 5 grep hits).
- **`code-review-chunk-dispatch`** (GA): code-review subagents return output — if every subagent grabs raw Bash output, multiple token burn.
- **`enum-known-values-via-insert-grep`** (GA): if that skill does `grep -rn ... | head -20` (instead of all), its own cost stays small.

## Background: TDD Trail (Bulletproofing Log)

### Cycle 1 — PASS (98% token-saving validated)

- **RED-Subagent** (without skill, scenario: health-check 5 containers on a remote server via SSH): wrote 5 sequential SSH calls (`docker logs --since 30m | grep error` without `| head`, `--tail 100` "in case the user asks" reflex), estimated 6k-28k token consumption. Self-assessment: "clearly not token-efficient — 20-50× more tokens than the efficient approach". Formulated the correct approach itself ("`for c in ...; do ... done` in ONE SSH call") — but **only as after-the-fact reflection**, not as default.

- **GREEN-Subagent** (with skill via Read tool, same task): 1 SSH call with server-side `for` loop, `docker ps --format "{{.Names}}: {{.Status}}"`, `--since 30m | grep -iE "error|critical" | tail -5`. Token consumption ~500 tokens vs ~50k naive = **~98% saving empirically**. Identified skill gap: SSH-multiplex pattern not explicitly documented (derived from anti-pattern).

### Cycle-2 Backlog (Polish, non-blocking)

1. **SSH-multiplex pattern as item #13** — `ssh host 'for ...; do ...; done'` instead of 5× `ssh host '...'`. Avoid SSH connection setup cost
2. **`docker compose ps` variant** as alternative to `docker ps --format`
3. **Health-check via curl**: `curl -sf http://host:port/healthz` when container exposes `/healthz` — cheaper than reading logs. Cross-link to `traefik-internal-route-probe`
4. **Container-set prefix filter** when `docker ps` shows >50 containers (Swarm-node edge case)

## Source Triggers

- Token-optimization sprint item: "critical analysis of token usage"
- Empirical from a morning session: ~30k tokens just for Bash outputs (cockpit + container status + docker logs)
- Pattern collection from a 145-session workflow review
