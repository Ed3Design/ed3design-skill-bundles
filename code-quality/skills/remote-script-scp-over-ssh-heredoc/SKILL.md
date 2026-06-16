---
name: remote-script-scp-over-ssh-heredoc
description: Use when writing or deploying scripts to a remote server via SSH and the script contains special characters (backticks, $, quotes, heredocs) that break SSH string quoting. Trigger on phrases like "SSH heredoc fails", "quoting hell in SSH", "backtick in remote script", "unexpected EOF on SSH", "tee over SSH doesn't work", "remote script with special characters", "scp instead of SSH heredoc", "SSH string broken". Do NOT load for simple single-line SSH commands without special characters, for Ansible/Fabric (their own templating mechanisms), or for local scripts.
---

# Remote Script: SCP over SSH-Heredoc

## Problem

SSH heredocs for multi-line scripts on remote servers fail because of **quoting hell**:

```bash
# ❌ Fails — backticks, $-variables, and quotes collide
ssh server 'sudo tee /usr/local/bin/script.sh << '"'"'EOF'"'"'
#!/bin/bash
USAGE=$(df "/" | awk "NR==2 {print $5}" | tr -d "%")
echo "Usage: $USAGE%"
EOF
sudo chmod +x /usr/local/bin/script.sh'
```

**Symptoms**: `unexpected EOF`, incorrectly expanded `$`-variables, empty `$USAGE`, truncated heredocs.

**Rule of thumb**: As soon as the script contains a `$`-variable, a backtick, or inner quotes → use the SCP pattern. SSH heredocs only work for simple configs without special characters.

## Pattern: write locally → SCP → chmod → execute

**Prerequisite**: Passwordless SSH access (via `~/.ssh/authorized_keys`). Check via `ssh-copy-id server` if not yet set up.

```bash
# Step 1: write the script LOCALLY — no quoting problem, arbitrary complexity
cat > /tmp/remote-script.sh << 'EOF'
#!/bin/bash
# All special characters allowed: backticks, $, quotes, heredocs
USAGE=$(df "/" | awk "NR==2 {print $5}" | tr -d "%")
THRESHOLD=75

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    MSG="⚠️ DISK ALARM: ${USAGE}% (limit: ${THRESHOLD}%) — $(date)"
    echo "$MSG" >> /tmp/alerts.log
fi
EOF

# Step 2: SCP to remote — no quoting involved, byte-identical transfer
# /tmp as staging: always writable, no sudo needed for scp
scp /tmp/remote-script.sh server:/tmp/remote-script.sh

# Step 3: chmod + move to target via SSH
# Only simple commands without special characters → no quoting problem
ssh server 'sudo mv /tmp/remote-script.sh /usr/local/bin/script.sh && sudo chmod +x /usr/local/bin/script.sh'

# Step 4: optional — test directly
ssh server '/usr/local/bin/script.sh'

# Cleanup
rm /tmp/remote-script.sh
```

**Why `/tmp` as staging**: `/tmp` on the remote server is always writable without sudo. `scp` can write there without root rights. The second SSH call (sudo mv + chmod) is a simple command without special characters.

## Why this works better

| Approach | Problem |
|---|---|
| `ssh server 'tee /path << '"'"'EOF'"'"' ...'` | Quoting collides with shell expansion |
| `ssh server "$(cat script.sh)"` | Local shell expands before SSH |
| `ssh server bash -s < script.sh` | Works for stdin, but no sudo, no tee to system path |
| **SCP + chmod** | ✅ No quoting problem, sudo works, arbitrary complexity |

## Variant: write a Python script locally

```python
script_content = '''#!/usr/bin/env python3
import subprocess
result = subprocess.run(["df", "/"], capture_output=True, text=True)
# arbitrarily complex
'''

with open('/tmp/remote-py.py', 'w') as f:
    f.write(script_content)

# scp /tmp/remote-py.py server:/usr/local/bin/remote-py.py
# ssh server 'chmod +x /usr/local/bin/remote-py.py'
```

## Cleanup convention

```bash
rm /tmp/remote-script.sh
# Optional: also on remote
ssh server 'rm /tmp/remote-script.sh 2>/dev/null'
```

## SSH heredoc: when it does work

Only for simple configs without `$`, without backticks, without inner quotes:

```bash
# ✅ Works: no $ in script
ssh server 'sudo tee /etc/myconfig << EOF
[section]
key=value
EOF'
```

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| Escaping `'` via `'"'"'` in an SSH string | Use the SCP pattern instead |
| `"` instead of `'` for the outer SSH quote to avoid `$` | Fails when the script itself contains `"` |
| `echo "$(cat script.sh)" \| ssh server bash` | Local expansion, remote syntax error |
| `scp` directly to `/usr/local/bin/` (needs sudo) | `/tmp` as staging, then `sudo mv` via SSH |

## Background

This pattern emerged from an automation session of 7 remote automations, all of which initially failed on SSH-heredoc quoting. The empirical insight: even when the SCP-pattern is known, the instinct is to first try to "repair" the quoting before reaching for SCP — the anti-pattern table above exists to short-circuit that reflex.

Possible fallbacks for later:

1. Base64-encode-and-transfer when SCP is blocked (firewall policies, jump-host)
2. Ansible as the "proper" approach for >3 remote scripts
