---
name: cross-repo-state-inspection-before-commit
description: |-
  Use when the user issues a vague git instruction like "commit hub", "push that to the repo", "should go in git", "put that under version control", "stage the changes", "deploy that to GitHub" — without specifying scope (which files, which repo, which branch, push-or-just-commit, new-repo-or-existing). Jumping to action without verifying repo state risks picking the wrong scope: committing everything when only one subdir was meant, creating a new repo when one already exists, pushing modifications meant to be deferred. The agent must run `git status` + `git log origin/main..HEAD` + `git remote -v` before acting. Trigger phrases like "commit X", "push that", "into the repo", "into git", "stage that", "bring to GitHub", "new commit needed". Do NOT load when the user has given fully-specified instructions, for clearly-single-project repos, when the working tree is clean, or for fresh `git init` workflows.

---

# Cross-Repo State Inspection Before Commit

> ✅ **PROMOTED** — TDD pressure-test PASS. RED: single-source tunnel-vision + `git add . && commit` reflex; GREEN: 4-Step + Step 3b (`ls-files --others --exclude-standard --directory`) + 4 scope-options A/B/C/D + more robust `branch --show-current` substitution. Cycle 2 polish: mono-repo as 5-step variant explicit, rebase-in-progress pre-check, detached-HEAD handling, mixed dual-state.

Before acting on a vague git instruction, take 60 seconds to verify the actual repo-state. Saves 5-30 minutes of "wait, that's not what I meant" rollback later.

## When to use

- User says "commit X", "push that to git", "X should go into the repo" without specifying scope
- You're not 100% sure if X is in an existing repo or needs a new one
- Working tree shows modifications you didn't make (other people's work, prior sessions)
- Mono-repo with potentially multiple untracked subprojects
- Repo has both local-only commits AND uncommitted changes (ambiguous "done?")

## When NOT to use

- User gave full git command-line ("git add A B && git commit -m 'Y' && git push") — execute, don't inspect
- Single-purpose repo, clean tree, fresh-from-clone state — no ambiguity
- `git init` from-scratch case (different concern, this skill assumes repo exists)
- CI/CD automated commit (no human-in-loop to clarify)

## The 4-step inspection

### Step 1: `git status --short`

```bash
git -C <path> status --short
```

Read the output literally — every line is a fact about the working tree:
- `M  file` — staged modification
- ` M file` — unstaged modification
- `A  file` — staged new file
- `?? file` — untracked
- `?? dir/` — entire untracked directory (the `/`-suffix is critical: hides individual files)

**Critical**: untracked DIRECTORIES (`?? subdir/`) often contain HUNDREDS of files. Never blindly `git add .` until you've enumerated them. Use `git status` (without `--short`) or `git ls-files --others --exclude-standard <subdir>/` to see contents.

### Step 2: `git log origin/<branch>..HEAD --oneline`

```bash
git -C <path> log origin/main..HEAD --oneline | head -10
```

This shows commits that are LOCAL ONLY (not yet on the remote). If non-empty:
- Someone (you or a prior session) already committed something that isn't on origin
- Push-or-not is a separate decision from new-commit-or-not
- Be explicit about both: "I'll push the 1 existing commit AND add a new commit for X"

If empty: working tree's changes are the only delta to consider.

### Step 3: `git remote -v`

```bash
git -C <path> remote -v
```

If `origin` exists with a fetch+push URL → existing remote, this is a continuation
If no remote → either (a) user wants a new repo created and pushed, or (b) intentionally local-only

If multiple remotes (`origin` + `upstream`, or `origin` + `mirror`) → ask user which to push to, never assume

### Step 4: Clarify scope with the user

After Steps 1-3, you have facts. Now ask the user with **specific scope options**:

```
git status shows:
- 8 untracked hub files
- 5 untracked subproject dirs (foo/, bar/, ...)
- 2 mods in _shared/ and ops/
- 1 local commit ahead of origin/main

"Hub should go into the repo" — did you mean:
  A) ONLY the 8 hub files + the ahead commit (probably user intent)
  B) hub + the 2 _shared/ops mods too
  C) All 5 subprojects additionally (large operation, probably not today)
```

Never assume A. Ask. The 60-second clarification prevents a 30-minute rollback.

## Real-world example: hub-commit

User: "The hub should go into the repo, can happen at the end of the current session"

**Without skill**: possible path → initialize a local `~/projects/hub/` as a git repo (only stub with 2 files), create new GitHub repo, push the wrong source.

**With inspection**: revealed that `<server-projects-root>/` on the server is already a mono-repo with:
- 1 ahead commit (`74ab162 feat(cockpit)`) → had to be pushed too
- 8 untracked hub files (Dockerfile, compose, requirements, app/__init__.py, app/collectors.py, app/static/, app/templates/index.html, app/main.py — wait, main.py was tracked-modified)
- 2 OTHER modifications (`_shared/traefik`, `ops/postgres-dumpall.sh`) → NOT committed (scope clarification)
- 5 OTHER untracked subproject dirs → NOT committed (scope clarification recorded as backlog)

Outcome: 2 clean pushes (`74ab162` → `59ca63f`), no rollback, no over-/under-commit drift.

## Quick-Reference

```bash
# 60-second inspection before every vague commit instruction:
git -C $PATH status --short
git -C $PATH log origin/$(git -C $PATH branch --show-current)..HEAD --oneline | head -5
git -C $PATH remote -v
# Then ask user with concrete scope options.
```

## Anti-patterns

- ❌ **`git add .` without reading `git status`** — pulls in all untracked files incl. subdirs into the commit
- ❌ **`git add -A` without scope clarification** — stages _shared/ + ops/ mods the user didn't mention
- ❌ **Assumption "user meant the whole repo"** vs "user meant only ONE subdir" — that's EXACTLY the ambiguity this skill resolves
- ❌ **Forget to push** when `git log origin/main..HEAD` shows an ahead commit — otherwise it stays orphaned locally
- ❌ **For a sub-dir-only commit forgetting the path prefix**: `git add Dockerfile` instead of `git add hub/Dockerfile` → staged at repo root, wrong path
- ❌ **With `git commit -a` at vague scope** — `-a` stages ALL tracked-modified files automatically, overrides scope clarification
- ❌ **Forget submodules**: for submodule repos additionally check `git submodule status`, otherwise a submodule pointer update lands accidentally in the commit

## Special case: mono-repo with untracked subprojects

When `git status` shows `?? subproject-A/`, `?? subproject-B/`, ... as whole dirs:

**Ask explicitly**:
> Untracked subprojects: `<list>`. Should these also go into the mono-repo, OR are these deliberately separate repos (locally in `~/projects/<subproj>/`)?

Mono-repo + separate sub-repos can coexist when `.gitignore` excludes the subproject dirs explicitly. If they are NOT in `.gitignore` but permanently untracked = unclear strategy → backlog item for a polish session.

## Connection to other skills

- `commit-message-honesty-precheck` (GA) — after scope clarification comes commit-message truth
- `pre-push-bypass-audit-trail` (GA) — if push still fails due to hook, do the bypass-audit first
- A remote-deploy iteration workflow — sibling for the server deployment loop (rsync → docker compose → curl), no git
- `production-seed-vs-demo-seed-split` (GA) — related to subproject clarification (when seed files in git vs gitignored)

## Promotion notes (DRAFT → GA)

Created from a hub-commit session where the user's "hub should go into the repo" became correctly scopeable only through inspection. Promote via `skill-tdd-promotion-workflow` after:
- 1 RED subagent: edge-cases like "submodule changes", "rebase in progress (.git/MERGE_HEAD)", "shallow clone", "bare repo"
- 1 production-anchor real-world catch where scope was unclear between two parallel refactors
- Cross-link to `commit-message-honesty-precheck`
