---
name: subprocess-ssh-arg-quoting-via-shlex
description: |-
  Use BEFORE writing or debugging Python subprocess.run(["ssh", host, "cmd", "arg1", "arg2"]) calls where the remote args contain shell-metacharacters — pipes `|`, parentheses `(` `)`, semicolons `;`, dollar-signs `$`, backticks, single/double-quotes, glob `*` `?`, tabs `\t`, or empty strings. The naive Python list passed after the host is silently joined by SSH client with spaces and re-evaluated by the REMOTE shell, where metacharacters get interpreted (pipe becomes shell-pipeline, parens cause syntax errors, tabs eaten as whitespace, etc.). Symptoms include 'syntax error: unexpected end of file', 'option requires an argument' for flag-values that contained tabs, 'command not found' for partial args that got shell-split, or silently wrong behavior when args are parsed differently than expected. STOP and use `shlex.quote()` on EACH remote-side arg, then `' '.join(quoted_args)` to produce ONE string that's passed as a SINGLE post-host arg to SSH — the remote shell then sees properly-quoted tokens. Trigger on phrases like "ssh + docker exec doesn't work", "psql via SSH gives syntax error", "remote command breaks", "SSH arg quoting problem", "subprocess.run with ssh args", "MCP server SSH tunnel", "deploy.sh failing on remote", "Bash syntax error from remote", "rsync with ssh and parameters", "pipe interpreted as shell pipe", "tab character disappears in SSH". Do NOT use for shell=True calls (use shlex.split() and proper escaping instead — different concern), for SSH config-file aliases without metacharacter-args (`ssh your-server` alone is safe), for SSH-without-remote-command (pure tunnel/SFTP), or for pure-local subprocess calls without SSH (Python's args-list mechanism handles those correctly via execve — the issue is SSH-specific double-shell-evaluation). Encodes a real session loss: 30+ minutes debugging through 4 iterations (-c "..." → -i stdin → -F "\t" tab-eaten → -F "|" shell-pipe-interpreted) before settling on shlex.quote-per-arg + join. Future SSH-bridging code (MCP servers, deploy scripts, backup scripts) all benefit from this skill applied first.
---

# Subprocess SSH Arg Quoting via shlex

> ✅ **PROMOTED** via TDD cycle (RED+GREEN subagent pair). RED subagent wrote naive list form and RED recognized on its own while writing "my code is probably broken for the `-F '|'` part" — skill prevents exactly this silent shell interpretation. GREEN subagent additionally used Step 4 (SQL via stdin instead of `-c`) and verified 10 edge cases.

## Overview

`subprocess.run(["ssh", "user@host", "remote", "cmd", "arg1", "arg2", ...])` does NOT pass args atomically. SSH joins all post-host args with spaces into one string, sends that string to the remote sshd, which spawns the user's login shell to execute it — meaning the **remote shell** interprets metacharacters.

The Python args-list mechanism (`subprocess.run([...])`) protects you from local shell. SSH undoes that protection. The fix is to quote per-remote-arg BEFORE handing it to SSH.

## The Pattern

### ❌ Naive (broken for any arg with metacharacters)

```python
subprocess.run(
    ["ssh", "user@host",
     "docker", "exec", "container",
     "psql", "-c", "SELECT * FROM t WHERE x = '2026-06-01'",
     "-F", "|"],
    ...
)
# SSH joins: docker exec container psql -c SELECT * FROM t WHERE x = '2026-06-01' -F |
#                                                                                    ^
#                                                       remote shell sees `|` as PIPE, breaks
```

### ✅ Correct (shlex.quote per arg + join)

```python
import shlex
import subprocess

remote_argv = [
    "docker", "exec", "container",
    "psql", "-U", "user", "-d", "db",
    "--no-psqlrc", "-A", "-F", "|",
]
remote_cmd = " ".join(shlex.quote(a) for a in remote_argv)
# remote_cmd = "docker exec container psql -U user -d db --no-psqlrc -A -F '|'"
#                                                                          ^^^
#                                                       pipe is now properly quoted

subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
     "user@host", remote_cmd],
    input=sql_payload, capture_output=True, text=True, timeout=30,
)
```

## Steps to apply

### Step 1: Identify the remote-arg-array

Separate Python-local args (`ssh`, options, host) from remote-command args.

```python
# Local-only (SSH client args):
ssh_prefix = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host]

# Remote command + its args:
remote_argv = ["docker", "exec", "-i", container, "psql", "-U", user, "-d", db, ...]
```

### Step 2: shlex.quote per remote-arg + join

```python
import shlex
remote_cmd = " ".join(shlex.quote(a) for a in remote_argv)
```

### Step 3: Pass remote_cmd as ONE arg to SSH

```python
result = subprocess.run(
    ssh_prefix + [remote_cmd],
    ...,
)
```

### Step 4: For SQL/script payloads, prefer stdin over -c

If your remote tool accepts stdin (psql, bash -c via heredoc, python -c, etc.), pass the payload via `input=...` rather than embedding in the arg-list. Avoids ALL quoting concerns for the payload itself.

```python
# Best: SQL via stdin
result = subprocess.run(
    ssh_prefix + [remote_cmd_with_psql_flags_but_no_minus_c],
    input=sql_text, capture_output=True, text=True,
)
```

### Step 5: Verify with a metachar-heavy test case

Test cases that catch broken quoting:
- `"SELECT * FROM t WHERE x = 'literal-quoted'"` (single quotes in SQL)
- `"COUNT(*)"` (parentheses)
- `"-F"`, `"|"` (pipe as separator)
- `"file with spaces.txt"` (whitespace in arg)
- `"key=val;DROP TABLE"` (semicolon)
- `"$HOME"` (dollar-sign — would expand on remote)

## Anti-Patterns

- ❌ **Manual escaping with backslashes**: `arg.replace("'", "\\'")` — fragile, misses edge cases, doesn't handle nested quoting
- ❌ **shlex.quote on ssh_prefix args**: those go through Python's execve (no shell), already safe
- ❌ **Using f-strings to build remote command** — easy to forget escaping for one variable, hard to audit. Concrete example:
  ```python
  # ❌ BROKEN: what if symbol='CL=F' contains, or e.g. 'O\'Reilly'?
  symbol = "CL=F"
  cmd = ["ssh", host, f"docker exec db psql -c \"SELECT * FROM t WHERE s='{symbol}'\""]
  # Audit question: must check each f-string argument individually for shell-safety
  ```
  ```python
  # ✅ CORRECT: shlex.quote per argument, then join
  remote_argv = ["docker", "exec", "db", "psql", "-c", f"SELECT * FROM t WHERE s='{symbol}'"]
  remote_cmd = " ".join(shlex.quote(a) for a in remote_argv)
  cmd = ["ssh", host, remote_cmd]
  # OR better: SQL via stdin (Step 4)
  ```
- ❌ **shell=True locally**: that's a different escaping problem, also dangerous for injection
- ❌ **Forgetting BatchMode=yes**: SSH will try interactive password/passphrase prompts and hang silently in subprocess
- ❌ **No SSH ControlMaster/ControlPersist for high-frequency callers**: each call does a new TCP+TLS+Auth roundtrip (~200-500ms). For MCP servers with frequent queries, set `~/.ssh/config`:
  ```
  Host your-server
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 600
  ```
  Reduces subsequent calls to ~5-20ms.

## Why pipe `|` and tab `\t` are particularly insidious

- **Pipe `|`**: silently interpreted as shell pipeline, the rest of args become input to a (often non-existent) next command. Symptom: weird "command not found" for what looks like a normal arg.
- **Tab `\t`**: gets eaten as whitespace by SSH joining (one or more whitespaces between args are merged). Python sends `"-F", "\t"`; SSH joins into `"-F  "` (extra space, no tab); remote shell tokenizes back into `-F` followed by nothing → "option requires an argument".

Both are silent — no Python-side error, no traceback, just wrong remote behavior. The shlex.quote pattern fixes BOTH in one move.

## Connection to other skills

- `your-server-fastapi-iteration` (GA): every SSH-based deploy step is candidate for this skill if it has metacharacter args
- `remote-script-scp-over-ssh-heredoc` (GA): heredoc is one valid alternative to stdin-piping
- `db-telemetry-primary-docker-logs-secondary` (GA): typical caller building `ssh + docker exec psql` chains
- `mcp-server-stdio-to-http-migration` (GA): MCP servers often have this exact issue at the SSH boundary

## Cost-of-Skipping

A real MCP-server refactor session:
- Iteration 1: `-c "SQL"` → quotes/parens broken → 5 min
- Iteration 2: `-i + stdin` for SQL, but `-F "\t"` still broken → 8 min (tab whitespace-eaten)
- Iteration 3: switch to `-F "|"` for tab-replacement → 7 min (pipe = remote shell pipeline)
- Iteration 4: `shlex.quote + join` → 5 min, finally works
- **Total cost: ~30 min + cognitive overhead** for one bug-class that 5 min of applying the skill would have prevented

At 3-4 SSH-bridge projects per year × 30 min = 1.5-2h annual savings + frustration reduction.

## Source triggers

- MCP-server refactor session: 4 iterations to correct quoting
- Pain: 30 min token consumption for a bug class that was structurally avoidable
- Brain-dump item "critical analysis of token usage" — such iteration loops are direct token pain

---

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS

- **RED subagent** (without skill, scenario: MCP-server function `query_trading_db(sql)` for a remote DB via SSH+docker exec+psql with `-F '|'` and test query with single quotes): wrote naive list form `["ssh", host, "docker", "exec", ..., "psql", ..., "-F", "|", "-c", sql]`. **While writing**, RED recognized on its own: "my code is probably broken for the `-F '|'` part. The SQL might get through because it's already quoted, but that's luck, not design." Identified the correct pattern (`shlex.quote + join`) **only as an option**, not as spontaneous default. Classic anti-pattern: known but not applied without skill trigger.

- **GREEN subagent** (with skill via Read tool): first read `description` frontmatter (trigger check), then "The Pattern" (visual ✅/❌ comparison), then "Steps to apply" as a checklist. Additionally used Step 4 (SQL via stdin instead of `-c`) — the most powerful lever because it removes the SQL payload completely from the quoting game. Wrote 10 edge-case tests (pipe, single-quote, parens, semicolon, dollar-sign, tab, glob, syntax-error, timeout, BatchMode). Caller-context check: `shlex` is Python stdlib, available out-of-the-box.

- **Refactor applied before PROMOTE**:
  - **Polish-1**: anti-pattern "f-string construction" extended with concrete code example with `symbol="CL=F"` — previously only one line mentioned, now with ❌/✅ comparison
  - **Polish-2**: anti-pattern "No ControlMaster/ControlPersist" added — for MCP-server callers (high frequency) reduces setup overhead from 200-500ms to 5-20ms per call

### Cycle-2-Backlog (Polish, non-blocking)

1. **Encoding hint** — `text=True` uses locale default. For mixed-locale setups more robust: `encoding="utf-8", errors="replace"`
2. **psql `-t` (tuples only) for machine parsing** — out-of-scope from the skill but practically relevant for MCP tools
3. **Cross-skill with `read-only-sql-via-regex-validator-DRAFT`** — skill solves only shell quoting, not SQL-injection safety. For MCP server: validator layer separately
4. **SSH stderr loss with `check=True` + `capture_output=True`** — psql notices get lost, possibly return them

---

_Created in a post-session skill review.  
Promoted after TDD Cycle 1 PASS via `skill-tdd-promotion-workflow` (RED+GREEN subagent pair, 2 polish items pre-PROMOTE incorporated)._
