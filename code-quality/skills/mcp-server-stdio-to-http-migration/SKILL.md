---
name: mcp-server-stdio-to-http-migration
description: |-
  Use when an MCP server uses `stdio` transport AND is spawned per-sub-agent via `uvx --from git+https://...`, `npx git+https://...`, or an equivalent on-demand-installer, AND you observe ANY of: (a) `.in_use/` lock-directories accumulating as zombies, (b) 10+ second startup per sub-agent (uvx re-resolves the Git source), (c) one server process per sub-agent instead of a shared instance, (d) the server "hangs" at session start. Fix-pattern: migrate to `streamable-http`/`http` transport with a persistent server (macOS LaunchAgent or systemd-unit) on a fixed localhost port, and point the client config at the HTTP URL. Result: one shared process, no zombies, startup O(seconds)→O(milliseconds). Trigger on phrases like "MCP zombie processes", "MCP stdio slow startup", "uvx --from git is slow", "streamable-http LaunchAgent". Do NOT load for servers designed for short-lived stdio (file-system MCP), for non-Git pip-installed servers that already start fast, for first-time MCP setup, or for server-selection questions.
---

# MCP Server stdio→HTTP Migration

## Overview

`stdio` transport for MCP servers makes sense for **short-lived, process-local** operations — the MCP-client library starts a subprocess, sends JSON-RPC over stdin/stdout, kills the subprocess at session end.

But when that subprocess is **restarted per sub-agent** AND the start-command is a `uvx --from git+https://...` or `npx git+https://...`:

- Every sub-agent dispatch triggers a fresh install from Git → 10-20s latency
- Lock-dirs (`~/.cache/uv/.in_use/<hash>/`) are left behind when the subprocess ends abnormally → hundreds of zombies
- Multiple parallel sub-agents = multiple parallel servers = resource waste + state inconsistency

Solution: **one persistent HTTP server per project**, all sub-agents talk to the same one.

## When to use

Trigger symptoms:
- `ls ~/.cache/uv/ | grep '\.in_use'` shows 50+ dirs (zombies)
- Sub-agent startup feels like it "loads 15s" — before it does anything
- `ps aux | grep <mcp-server-name>` shows 5+ identical processes in parallel
- The MCP-server config uses `uvx --from git+...` or a similar on-demand install

Trigger phrases:
- "the MCP server is slow"
- "MCP restarts per sub-agent"
- "zombie .in_use directories"
- "set up MCP HTTP transport"
- "make the MCP server persistent as a LaunchAgent"

## When NOT to use

- **MCP servers with intentionally session-local state**: e.g. an FS-MCP that only operates on a temporary working dir. stdio is correct here — 1 subprocess per session is the design goal.
- **Already-installed MCP servers** (`pip install <pkg>` or `npm install -g <pkg>`): no Git-resolution overhead, stdio startup is <1s. No migration needed.
- **First-time setup of a new MCP server**: read the upstream docs, don't jump straight to HTTP.
- **MCP-selection questions** ("which MCP server for Postgres?"): different topic.

## The 4-Step Migration

This example uses a generic Git-installed MCP server (here called `my-mcp-server`) and assumes two projects, each needing its own persistent server instance.

### Step 1 — One-time install (no more on-demand)

```bash
# Instead of uvx --from git+... per call:
uv tool install my-mcp-server --from git+https://github.com/<org>/<repo>
# or pipx install ... or npm install -g ...
```

Verify:
```bash
which my-mcp-server          # $HOME/.local/bin/my-mcp-server
my-mcp-server --version       # 0.x.x
```

Test startup latency:
```bash
time my-mcp-server --help     # should be <1s
```

### Step 2 — Create persistent LaunchAgent (macOS) or systemd-unit (Linux)

`~/Library/LaunchAgents/com.example.my-mcp-server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.example.my-mcp-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/.local/bin/my-mcp-server</string>
        <string>start-mcp-server</string>
        <string>--transport</string>
        <string>streamable-http</string>
        <string>--port</string>
        <string>9001</string>
        <string>--context</string>
        <string>ide-assistant</string>
        <string>--project</string>
        <string>$HOME/projects/your-project</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HOME/projects/your-project</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/my-mcp-server.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/my-mcp-server.stderr.log</string>
</dict>
</plist>
```

> Note: LaunchAgent plist values do not expand `$HOME` — substitute the absolute path before loading. For a second project, copy the plist with a new Label (`com.example.my-mcp-server-b`), a new port (9002), and its own `--project` path.

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.example.my-mcp-server.plist
launchctl list | grep my-mcp-server   # exit 0, PID set
curl -s http://127.0.0.1:9001/mcp -X POST -d '{}' -H 'Content-Type: application/json' | head
```

### Step 3 — Update MCP-Client-Config to URL

**Project-local** (`<project>/.mcp.json`):
```json
{
  "mcpServers": {
    "my-mcp": {
      "url": "http://127.0.0.1:9001/mcp"
    }
  }
}
```

**User-local Claude Code** (`<project>/.claude/settings.local.json`):
```json
{
  "mcpServers": {
    "my-mcp": {
      "url": "http://127.0.0.1:9001/mcp"
    }
  }
}
```

> ⚠️ **NOT** `settings.json` (project-checked-in) — `mcpServers` is not a valid top-level field there, schema validation fails.

### Step 4 — Disable stdio variant + cleanup

In `<project>/.mcp.json` (or `~/.claude.json`):
```json
{
  "enabledPlugins": {
    "my-mcp": false   // prevents the on-demand-stdio from triggering again
  }
}
```

Zombie cleanup:
```bash
# Safe: only kill the leftover locks
find ~/.cache/uv -name '*.in_use' -type d -mtime +1 -exec rm -rf {} +
```

Verify success:
```bash
ps aux | grep my-mcp-server       # 1 process (LaunchAgent), not N
ls ~/.cache/uv/.in_use 2>/dev/null | wc -l   # 0
```

## Anti-Patterns

| Anti-Pattern | Why not |
|---|---|
| `uvx --from git+...` in production Claude Code config | Git-resolution every time, 10-20s latency, zombie-lock risk |
| Starting the MCP server as a foreground process ("I won't forget to kill it") | LaunchAgent / systemd is more robust, KeepAlive=true heals crashes |
| Ignoring port-conflict risk | 9001 for one app, 9002 for the next; reserve 9001-9019 for yourself |
| Writing `mcpServers` into `settings.json` | Schema validation fails. Use `settings.local.json` OR `.mcp.json`. |
| Configuring the HTTP server without logs | If the MCP server crashes without `StandardOutPath`, debugging is blind |

## Cost of NOT migrating (before-fix measurement)

- 16s startup latency per sub-agent dispatch (uvx git-resolve)
- 143 zombie directories `~/.cache/uv/.in_use/<hash>/`
- 1 MCP-server process per parallel-running sub-agent → no shared LSP state
- Pain: sessions started "loading..." instead of immediately

## Cost AFTER migration

- 0.69s startup (LaunchAgent runs persistently, sub-agent only does an HTTP connect)
- 0 zombies
- 1 process per project
- Tools/resources are read consistently by all sub-agents
