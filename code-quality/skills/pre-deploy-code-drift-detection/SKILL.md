---
name: pre-deploy-code-drift-detection
description: |-
  Use when about to deploy a service that has multiple parallel push-sources (Mac + work-laptop + server-direct-edit + remote Claude session), to detect 3-way Git-drift between local, origin/main, and server-checkout BEFORE rsync/checkout/build destroys parallel work. Trigger on phrases like "deploy to server", "rsync to server", "server has working-tree changes", "why does origin have commits I don't have", "Mac + server-direct-edit drift", "code drift between machines". Do NOT load for first-time-setup-deploy (no parallel sources yet exist), for single-developer-single-machine workflows, for server-only-via-CI deploys (CI is the sole push-source), or for in-container-hot-reload-iteration (no rsync involved). This skill encodes a hard-won lesson: 4h lost because 15 server-commits were made before discovering that origin/main had parallel local commits (3-source drift between local, origin, and server). A 2-minute pre-flight would have prevented it.
---

# Pre-Deploy Code-Drift-Detection

## When to use

Before ANY deploy (rsync, docker compose up, git pull-and-restart) where:
- The codebase has **>1 active push-source** (Mac + work-laptop + server-direct-edit + remote Claude session)
- The Server has a **long-lived Working-Tree** (not ephemeral CI/CD pipeline)
- The last deploy was **>3 days ago** (drift compounds)

## When NOT to use

- First-time-Setup-Deploy (no parallel sources yet)
- Single-developer-single-machine workflows
- Server-only-via-CI deploys (CI = sole push-source)
- In-Container-Hot-Reload-iteration (no rsync)

## The 3-Way-Compare Pre-Flight (90 seconds, mandatory)

```bash
# 1) Mac-Side fetch+state
git -C <mac-repo> fetch origin <branch>
git -C <mac-repo> log --oneline <branch>..origin/<branch>     # origin AHEAD of Mac?
git -C <mac-repo> log --oneline origin/<branch>..<branch>     # Mac AHEAD of origin?
git -C <mac-repo> status --short --branch                     # Mac uncommitted?

# 2) Server-Side fetch+state
ssh <user>@<server> "cd <server-repo> && git fetch origin <branch> && \
  echo '=== origin ahead of server ===' && git log --oneline <branch>..origin/<branch> && \
  echo '=== server ahead of origin ===' && git log --oneline origin/<branch>..<branch> && \
  echo '=== server uncommitted ===' && git status --short --branch && \
  echo '=== server untracked ===' && git status --porcelain | grep '^??'"

# 3) Interpret 4 scenarios:
#   A) Both Mac+Server = origin (clean) → safe rsync/pull, proceed
#   B) Mac ahead of origin, Server = origin → Mac push + Server pull, proceed
#   C) Server has uncommitted/untracked → STOP, classify in buckets, decide:
#        c1) commit them (if real work) — backup-branch first
#        c2) discard them (if temp/test) — reset --hard with explicit user confirm
#        c3) preserve them out-of-band (cp to /tmp) — then deploy
#   D) Mac ahead of origin AND origin ahead of Mac (= 3rd push-source exists) → STOP, the dangerous case
```

## The 3rd-Push-Source Discovery (Scenario D)

This is the dangerous case. Symptoms:
- `Mac main..origin/main` shows commits
- `Mac origin/main..main` ALSO shows commits
- → Mac and origin have **diverged** because something else pushed to origin

**Discovery questions:**
1. Are there commit-messages on origin that look like they came from a **different model** / **different style** than usual?
2. Are there **work-laptop** / **iPad-Claude-Session** / **CI-bot** pushes?
3. Check `git log origin/main --format='%h %ci %an %s' -10` for author/timestamp patterns

**Resolution options:**
- (a) **Mac rebase onto origin** — preserves Mac-local + integrates origin-newer (safest if Mac-local commits don't conflict)
- (b) **Mac merge origin** — creates merge-commit but preserves both histories
- (c) **Cherry-pick selective** — if Mac-local is mostly junk, cherry-pick the few good commits onto origin

## The Server-Direct-Edit Anti-Pattern

If `git status` on server shows **>10 modified files + >5 untracked files** with mtime spread over multiple days:

**Diagnosis**: someone is editing on the Server directly (a Claude session running on the Server, or SSH-edit). This is an anti-pattern because:
- Server-Direct-Edits are typically uncommitted → no audit trail
- They block rsync because `--delete` would erase untracked work
- They duplicate work already in flight on Mac → 3-source-Drift escalates

**Response**:
1. **DO NOT** rsync over the Server-state — back up first
2. **Triage** the Server-uncommitted into thematic buckets (mtime-cluster + content-grep)
3. **Commit each bucket atomically** (with proper author/co-author attribution) → push origin → pull on Mac
4. **THEN** Mac is the canonical truth and rsync/pull proceeds safely

## Output-Format

After the 3-Way-Compare, surface to user:

```
## Drift-Status
- Mac → origin: {N commits ahead | clean | M behind}
- Server → origin: {N commits ahead | clean | M behind}
- Server Working-Tree: {clean | {N modified, M untracked}}
- Scenario: {A | B | C | D}
- Recommendation: {proceed | commit-then-deploy | stop-decide}

## Risks if we just rsync now
- {list of concrete files / commits that would be lost}
```

## Anti-Patterns

- ❌ **Skipping Pre-Flight because "I just deployed yesterday"** — Server-Direct-Edits can happen in hours
- ❌ **`git pull` without checking `--rebase` vs `--merge`** — depends on whether Mac has local commits
- ❌ **rsync `--delete` without Pre-Flight** — destroys untracked Server-Direct-Edit work
- ❌ **`git reset --hard origin/main` on Server without backup-branch first** — irreversible loss of Direct-Edit work
- ❌ **Assuming origin = Mac** — only true if Mac just pushed; in Multi-Source-Setup origin can diverge

## Real-World Impact

- **4h lost** through:
  - 15 server-commits made without pre-flight
  - Push attempt rejected → discovery: origin had 10 parallel local commits (3rd push-source) AND Mac had 10 local unpushed
  - Hard-reset to origin/main + backup-branch + re-commit of only gitignore-safety
- **With pre-flight the outcome would be**: 90-second discovery → decision to push Mac→origin first, then server pull, then normal rsync. Saves 4h.
- **Reproducible**: every push from a 3-source setup carries this risk. Without the skill: the next 4h-drift in 1-2 weeks.

## Cross-references

- `superpowers:using-git-worktrees` — alternative when parallel branches should run more isolated
- Pair with a code-review chunk-dispatch workflow when a server-direct-edit backlog must be reviewed before merging
