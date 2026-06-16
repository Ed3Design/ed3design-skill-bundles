---
name: bash-output-filtering-disciplines
description: |-
  Use BEFORE running any Bash command that could produce more than ~50 lines of stdout: `docker logs`, `docker ps -a`, `git log`, `find`, `ps aux`, `psql -c "SELECT * FROM..."`, `cat large.log`, `ls -la` deep dirs, `journalctl`, `dmesg`, `kubectl logs`, `du -a`. STOP and apply head/tail/grep/wc/jq/awk/sed pre-filters in the same pipeline — never let raw output flow into the conversation context. Every line above the relevant data is wasted tokens; a single morning session can burn ~50k tokens on container status alone. Trigger on phrases like "docker logs of container X", "look at git log", "ps aux", "journalctl", "SELECT * FROM table", "why is the session token consumption high". Do NOT apply when the user explicitly asked for full output, for inherently small commands (`whoami`, `pwd`, `date`), one-shot value-extractions, or when piping to a file.

---

# Bash Output Filtering Disciplines

> ✅ **PROMOTED** via TDD-Cycle. RED subagent reflected: "my default is significantly less token-efficient — 50x more tokens than necessary". GREEN subagent achieved with skill **~98% saving** (~500 tokens instead of ~50k) via 1 SSH-Call with server-side for-loop instead of 5 sequential SSH calls.

## Overview

**Pain anchor**: a single health-check sweep can burn ~15-20k tokens just from unfiltered Bash outputs (container lists, logs without tail, SELECT * instead of count, find without head). Over 30 sessions/month ≈ ~500k tokens of pure boilerplate.

**Core discipline**: Filter **in the same command pipeline**, not "I'll filter mentally after reading". Once output is in the conversation context, the tokens are consumed — whether you read them or not.

## When to Trigger

✅ **YES — Filter-first:**
- Command could produce > 50 output lines
- Command has `*`-wildcard or tree-recursion (`find /`, `ls -laR`)
- DB-query without `LIMIT`, `count(*)` or `EXPLAIN`
- Log-reading without `--tail` / `--since`
- Process-listing without `grep PROCESS_NAME`
- File-listing in unknown (potentially large) directory

❌ **NO — fully OK:**
- User explicitly said "complete output please"
- One-shot value-extract (`whoami`, `date`, `pwd`, `echo $VAR`)
- Tool-output is known-small (< 50 lines guaranteed)
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

### 2. `docker ps` — restrict format

```bash
# ❌ bad: full format with lots of whitespace
docker ps -a

# ✅ good: only name + status
docker ps --format "table {{.Names}}\t{{.Status}}"

# ✅ better for 1-line health-check:
docker ps --format "{{.Names}}: {{.Status}}" | grep -v healthy
# → shows ONLY unhealthy/restarting containers
```

### 3. `git log` — ALWAYS with `-n N` or `--oneline`

```bash
# ❌ bad: full history with full format
git log

# ✅ good: 10 latest commits one-line
git log --oneline -n 10

# ✅ better: only SHA + subject + date
git log --pretty=format:"%h %ad %s" --date=short -n 20
```

### 4. `find` — ALWAYS with output-cap

```bash
# ❌ bad: can dump thousands of files
find <your-project-dir> -name "*.py"

# ✅ good: max 20 files
find <your-project-dir> -name "*.py" | head -20

# ✅ better: just count
find <your-project-dir> -name "*.py" | wc -l

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

### 7. `journalctl` / `dmesg` — time filter

```bash
# ❌ bad: all boot logs
journalctl

# ✅ good: only last hour, only errors
journalctl --since "1 hour ago" -p err --no-pager | tail -50
```

### 8. `cat large.log` / full-file-read

```bash
# ❌ bad: dumps complete log file into context
cat /var/log/app.log

# ✅ good: just end
tail -100 /var/log/app.log

# ✅ better: only relevant lines
tail -1000 /var/log/app.log | grep -iE "error|critical"

# ✅ for Read-tool: use offset + limit
# Read file_path="/var/log/app.log" offset=5000 limit=200
```

### 9. JSON output — `jq -c` for one-line

```bash
# ❌ bad: pretty-printed JSON with each line expanded
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

# ✅ better: names single-column
ls ~/.claude/skills/ | head -20
```

### 11. `du -sh` instead of `du -a`

```bash
# ❌ bad: every file individually
du -a ~/Downloads

# ✅ good: just summary
du -sh ~/Downloads

# ✅ top-10 largest dirs
du -sh ~/Downloads/* | sort -rh | head -10
```

### 12. `wc -l` as a pre-probe

When unclear whether output is large:

```bash
# Probe first (one integer output)
cmd | wc -l
# → if < 50: cmd without filter
# → if > 50: add filter
```

## Heuristic: which filter when

| Output type | Default filter | Rationale |
|---|---|---|
| Logs (time-based) | `--tail 50` or `--since 30m` | Recent is usually more relevant than history |
| Logs (pattern) | `grep -iE "error\|warn" \| tail -20` | Pre-filter ERROR class |
| Lists (files, containers, processes) | `\| head -20` | Sample suffices for overview |
| Lists (count asked) | `\| wc -l` | Only the number |
| Tables (DB) | `LIMIT 10` or `count(*)` | Full dumps are rarely productive |
| JSON streams | `jq -c '.field' \| head -20` | Compact + relevant |
| Find/search | `\| head -20` | First hits suffice, otherwise refine pattern |

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| `cmd > /tmp/x.txt && cat /tmp/x.txt` | File-write OK, then `Read offset+limit` or `tail/head` directly |
| Re-running the same command "because I want to see it again" | Output is in history — recall, don't re-run |
| `docker logs container \| less` | `less` does nothing for token-context (no interactive reader in Bash tool) |
| `find / -name "X"` without cap | ALWAYS `\| head`, or better Glob tool |
| `psql -c "SELECT *"` | `LIMIT` or `count` — otherwise memory + token burn |
| Relying on user-confirm "ok, can you show the last 10?" | Pre-filter, then optionally "more on request"-note |
| Five SSH+docker exec calls instead of 1 HTTP aggregator call | If MCP/health aggregator exists: use it instead of SSH chain |
| Output `2>&1` without stderr-need | Stderr only merge when you want to read errors along |

## Cost-of-Skipping

Empirical estimates from work sessions:

| Operation | without skill (typical) | with skill | Saving |
|---|---|---|---|
| Container health check (5 containers) | ~3-5k (`docker ps -a` + 5× `docker inspect`) | ~200 (`docker ps --format "..."`) | **~95%** |
| Recent-error sweep | ~5-8k (`docker logs` unfiltered × N containers) | ~500-800 (`docker logs --since 30m \| grep ERROR \| tail -20`) | **~90%** |
| Git-log review per repo | ~2-3k | ~200 (`git log --oneline -n 10`) | **~93%** |
| Find search in large tree | ~3-10k | ~300 (`\| head -20` or Glob tool) | **~95%** |
| DB trade statistic | ~800-2000 (`SELECT *`) | ~50-100 (`count(*)`) | **~95%** |

**Projection**: 30 sessions/month × 3-5 of these operations per session × 5k saved = **~450-750k tokens/month structurally avoided**.

## Connection to other Skills

- **`db-telemetry-primary-docker-logs-secondary`** (GA): preaches DB-telemetry as primary **instead of** Docker logs. This skill is the complementary discipline **when** Docker logs are needed (secondary).
- **Sub-Agent model matrix**: bulk-smoketest subagents use lightweight models — if Bash-output stays large, token-cost multiplies per subagent. Filter discipline reduces subagent cost too.
- **`reporting-artefact-detection-before-claiming-anomaly`** (GA): before claiming an anomaly, check whether the Bash-output sample was large enough (anti-pattern: deriving anomaly from 5 grep hits).
- **`code-review-chunk-dispatch`** (GA): code-review subagents return output — if each subagent dumps raw Bash-output, multiplied token burn.
- **`enum-known-values-via-insert-grep`** (GA): when this skill does `grep -rn ... | head -20` (instead of all), its own cost stays small.

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS (98% token saving validated)

- **RED subagent** (without skill, scenario: health-check 5 containers on a server via SSH): wrote 5 sequential SSH calls (`docker logs --since 30m | grep error` without `| head`, `--tail 100` "in case user asks" reflex), estimated 6k-28k token consumption. Self-assessment: "significantly not token-efficient — 20-50x more tokens than the efficient approach". Itself formulated the correct approach ("`for c in ...; do ... done` in ONE SSH call") — but **only as retrospective reflection**, not as default.

- **GREEN subagent** (with skill via Read tool, same task): 1 SSH call with server-side `for`-loop, `docker ps --format "{{.Names}}: {{.Status}}"`, `--since 30m | grep -iE "error|critical" | tail -5`. Token consumption ~500 tokens vs ~50k naïve = **~98% saving empirically**. Identified skill gap: SSH-multiplex pattern not explicitly documented (derived from anti-pattern).

### Cycle-2-Backlog (Polish, non-blocking)

1. **SSH-multiplex pattern as Item #13** — `ssh host 'for ...; do ...; done'` instead of 5× `ssh host '...'`. Avoid SSH-connection-setup cost
2. **`docker compose ps`-variant** as alternative to `docker ps --format`
3. **Health-check via curl**: `curl -sf http://host:port/healthz` when container exposes `/healthz` — cheaper than reading logs. Pair with an internal route-probe check when behind a reverse proxy
4. **Container-set prefix filter** when `docker ps` shows >50 containers (swarm-node edge case)

## Source triggers

- Token-optimization sprint item: critical analysis of token usage
- Empirical observation: ~30k tokens just for Bash outputs in a single morning session (cockpit + container status + docker logs)
- Pattern collection from a long-running workflow review
