---
name: subprocess-ssh-arg-quoting-via-shlex
description: Use BEFORE writing or debugging Python subprocess.run(["ssh", host, "cmd", "arg1", "arg2"]) calls where the remote args contain shell-metacharacters — pipes `|`, parentheses `(` `)`, semicolons `;`, dollar-signs `$`, backticks, single/double-quotes, glob `*` `?`, tabs `\t`, or empty strings. The naive Python list passed after the host is silently joined by SSH client with spaces and re-evaluated by the REMOTE shell, where metacharacters get interpreted (pipe becomes shell-pipeline, parens cause syntax errors, tabs eaten as whitespace, etc.). Symptoms include 'syntax error: unexpected end of file', 'option requires an argument' for flag-values that contained tabs, 'command not found' for partial args that got shell-split, or silently wrong behavior when args are parsed differently than expected. STOP and use `shlex.quote()` on EACH remote-side arg, then `' '.join(quoted_args)` to produce ONE string that's passed as a SINGLE post-host arg to SSH — the remote shell then sees properly-quoted tokens. Trigger on phrases like "ssh + docker exec funktioniert nicht", "psql via SSH gibt syntax error", "remote command bricht ab", "SSH-arg-Quoting-Problem", "subprocess.run mit ssh args", "MCP-Server SSH-Tunnel", "deploy.sh failing on remote", "Bash syntax error from remote", "rsync mit ssh und Parametern", "pipe wird als shell-pipe interpretiert", "tab character verschwindet im SSH". Do NOT use for shell=True calls (use shlex.split() and proper escaping instead — different concern), for SSH config-file aliases without metacharacter-args (`ssh swatserver` alone is safe), for SSH-without-remote-command (pure tunnel/SFTP), or for pure-local subprocess calls without SSH (Python's args-list mechanism handles those correctly via execve — the issue is SSH-specific double-shell-evaluation). Encodes Wolf's 11.06.2026 MCP-Server-Refactor session loss: 30+ minutes debugging through 4 iterations (-c "..." → -i stdin → -F "\t" tab-eaten → -F "|" shell-pipe-interpreted) before settling on shlex.quote-per-arg + join. Cost: 30 min + frustration. Future SSH-bridging code (MCP servers, deploy scripts, backup scripts, swatserver-iterations) all benefit from this skill applied first.
---

# Subprocess SSH Arg Quoting via shlex

> ✅ **PROMOTED 2026-06-12** via TDD-Cycle (RED+GREEN-Subagent-Pair). RED-Subagent schrieb naive Liste-Form und erkannte selbst beim Schreiben „mein Code ist wahrscheinlich kaputt für den `-F '|'` Teil" — Skill verhindert genau diese silent-Shell-Interpretation. GREEN-Subagent nutzte zusätzlich Step 4 (SQL via stdin statt `-c`) und verifizierte 10 Edge-Cases.

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
- ❌ **Using f-strings to build remote command** — easy to forget escaping for one variable, hard to audit. Concrete Beispiel:
  ```python
  # ❌ BROKEN: was wenn symbol='CL=F' enthält, oder z.B. 'O\'Reilly'?
  symbol = "CL=F"
  cmd = ["ssh", host, f"docker exec db psql -c \"SELECT * FROM t WHERE s='{symbol}'\""]
  # Audit-Frage: muss man bei jedem f-string-Argument einzeln prüfen ob es Shell-safe ist
  ```
  ```python
  # ✅ CORRECT: shlex.quote pro Argument, dann join
  remote_argv = ["docker", "exec", "db", "psql", "-c", f"SELECT * FROM t WHERE s='{symbol}'"]
  remote_cmd = " ".join(shlex.quote(a) for a in remote_argv)
  cmd = ["ssh", host, remote_cmd]
  # ODER besser: SQL via stdin (Step 4)
  ```
- ❌ **shell=True locally**: that's a different escaping problem, also dangerous for injection
- ❌ **Forgetting BatchMode=yes**: SSH will try interactive password/passphrase prompts and hang silently in subprocess
- ❌ **No SSH ControlMaster/ControlPersist für hochfrequente Caller**: jeder Call macht neuen TCP+TLS+Auth-Roundtrip (~200-500ms). Für MCP-Server mit häufigen Queries `~/.ssh/config` setzen:
  ```
  Host swatserver
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 600
  ```
  Reduziert nachfolgende Calls auf ~5-20ms.

## Why pipe `|` and tab `\t` are particularly insidious

- **Pipe `|`**: silently interpreted as shell pipeline, the rest of args become input to a (often non-existent) next command. Symptom: weird "command not found" for what looks like a normal arg.
- **Tab `\t`**: gets eaten as whitespace by SSH joining (one or more whitespaces between args are merged). Python sends `"-F", "\t"`; SSH joins into `"-F  "` (extra space, no tab); remote shell tokenizes back into `-F` followed by nothing → "option requires an argument".

Both are silent — no Python-side error, no traceback, just wrong remote behavior. The shlex.quote pattern fixes BOTH in one move.

## Connection to other skills

- `swatserver-fastapi-iteration` (GA): every SSH-based deploy step is candidate for this skill if it has metacharacter-args
- `remote-script-scp-over-ssh-heredoc` (GA): heredoc is one valid alternative to stdin-piping
- `db-telemetry-primary-docker-logs-secondary` (GA): typical caller building `ssh + docker exec psql` chains
- `mcp-server-stdio-to-http-migration` (GA): MCP-Servers often have this exact issue at the SSH-boundary

## Cost-of-Skipping

Wolf-Session 11.06.2026 MCP-Server-Refactor:
- Iteration 1: `-c "SQL"` → quotes/parens broken → 5 min
- Iteration 2: `-i + stdin` for SQL, but `-F "\t"` still broken → 8 min (tab whitespace-eaten)
- Iteration 3: switch to `-F "|"` for tab-replacement → 7 min (pipe = remote shell pipeline)
- Iteration 4: `shlex.quote + join` → 5 min, finally works
- **Total cost: ~30 min + cognitive overhead** for one bug-class that 5 min of skill-application would prevent

At 3-4 SSH-bridge-projects per year × 30 min = 1.5-2h annual savings + frustration reduction.

## Quell-Triggers

- 11.06.2026 ~14:30 UTC: MCP-Server v0.2.0 Refactor — 4 Iterationen bis korrektes Quoting
- Wolf-Pain: 30 min Token-Verbrauch für eine Bug-Klasse die strukturell vermeidbar war
- Brain-Dump-Item „kritische Analyse der Token-Nutzung" (05.06.2026) — solche Iterations-Loops sind direkter Token-Pain

---

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill, Scenario: MCP-Server-Funktion `query_trading_db(sql)` für swatserver/ultimative-db via SSH+docker exec+psql mit `-F '|'` und Test-Query mit Single-Quotes): Schrieb naive Liste-Form `["ssh", host, "docker", "exec", ..., "psql", ..., "-F", "|", "-c", sql]`. **Während des Schreibens** erkannte RED selbst: „Mein Code ist wahrscheinlich kaputt für den `-F '|'` Teil. Die SQL könnte durchkommen weil sie schon gequoted ist, aber das ist Glück, nicht Design." Identifizierte das korrekte Pattern (`shlex.quote + join`) **nur als Option**, nicht als spontanen Default. Klassisches Anti-Pattern: bekannt aber nicht ohne Skill-Trigger angewendet.

- **GREEN-Subagent** (mit Skill via Read-Tool): Las erst `description`-Frontmatter (Trigger-Check), dann „The Pattern" (visueller ✅/❌-Vergleich), dann „Steps to apply" als Checkliste. Nutzte zusätzlich Step 4 (SQL via stdin statt `-c`) — der mächtigste Hebel weil er den SQL-Payload komplett aus dem Quoting-Spiel nimmt. Schrieb 10 Edge-Case-Tests (Pipe, Single-Quote, Parens, Semicolon, Dollar-Sign, Tab, Glob, Syntax-Error, Timeout, BatchMode). Caller-Context-Check: `shlex` ist Python-stdlib, also out-of-the-box verfügbar.

- **Refactor angewendet vor PROMOTE**:
  - **Polish-1**: Anti-Pattern „f-string-Konstruktion" um konkretes Code-Beispiel mit `symbol="CL=F"` erweitert — vorher nur einzeilig erwähnt, jetzt mit ❌/✅-Vergleich
  - **Polish-2**: Anti-Pattern „No ControlMaster/ControlPersist" hinzugefügt — für MCP-Server-Caller (hochfrequent) reduziert das Setup-Overhead von 200-500ms auf 5-20ms pro Call

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Encoding-Hinweis** — `text=True` nutzt Locale-Default. Bei mixed-locale-Setups robuster: `encoding="utf-8", errors="replace"`
2. **psql `-t` (tuples only) für maschinelles Parsing** — out-of-scope vom Skill aber praktisch relevant für MCP-Tools
3. **Cross-Skill mit `read-only-sql-via-regex-validator-DRAFT`** — Skill löst nur Shell-Quoting, nicht SQL-Injection-Sicherheit. Für MCP-Server: Validator-Layer separat
4. **SSH-stderr-Loss bei `check=True` + `capture_output=True`** — psql-NOTICEs gehen verloren, evtl. zurückgeben

---

_Erstellt 2026-06-11 ~16:30 UTC im Post-Session-Skill-Review.  
Promoted 2026-06-12 nach TDD-Cycle 1 PASS via `skill-tdd-promotion-workflow` (RED+GREEN-Subagent-Pair, 2 Polish-Items pre-PROMOTE eingebaut)._
