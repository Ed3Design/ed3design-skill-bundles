---
name: cross-repo-state-inspection-before-commit
description: Use when the user issues a vague git instruction like "commit hub", "push das ins Repo", "hub soll ins Git", "bring das in Versionierung", "stage the changes", "deploy that to GitHub" — without specifying scope (which files, which repo, which branch, push-or-just-commit, new-repo-or-existing). The risk: jumping to action without verifying repo-state means picking the wrong scope (committing everything when user meant only one subdir, creating a new repo when one already exists, pushing modifications that user wanted to defer). Encodes the 4-step inspection pattern from 2026-06-11 hub-commit session where Wolf said "hub soll ins Repo" — initial interpretation could have been "create new repo" but `git status` + `git log origin/main..HEAD` + `git remote -v` revealed: (a) the parent dir `/srv/projects/` IS already a git repo (`Ed3Design/swatserver-infra`), (b) 1 commit was already ahead of origin, (c) 8 hub-files were untracked, (d) 5 OTHER untracked subproject-dirs were NOT to be committed. Trigger phrases like "commit X", "push das", "ins Repo bringen", "ins Git", "versionieren", "stage that", "bring to GitHub", "create a commit for", "new commit needed", "git workflow für X". Do NOT load when the user has given fully-specified instructions ("git add hub/ && git commit -m 'X' && git push"), for repos that are clearly single-project (no mono-repo, no untracked siblings), or when the working tree is clean (no inspection-ambiguity). Also do NOT load for fresh repos that have never been initialized (different concern — that's `git init` workflow).
---

# Cross-Repo State Inspection Before Commit

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. RED: Single-Source-Tunnelblick + `git add . && commit`-Reflex; GREEN: 4-Step + Step 3b (`ls-files --others --exclude-standard --directory`) + 4 Scope-Optionen A/B/C/D + robustere `branch --show-current`-Substitution. Cycle 2 Polish: Mono-Repo als 5-Step-Variante explizit, Rebase-in-progress-Pre-Check, Detached-HEAD-Handling, MM-Doppel-State.

Before acting on a vague git instruction, take 60 seconds to verify the actual repo-state. Saves 5-30 minutes of "wait, that's not what I meant" rollback later.

## When to use

- User says "commit X", "push das ins Git", "X soll ins Repo" without specifying scope
- You're not 100% sure if X is in an existing repo or needs a new one
- Working tree shows modifications you didn't make (other people's work, prior sessions)
- Mono-repo with potentially multiple untracked subprojects
- Repo has both local-only commits AND uncommitted changes (ambiguous "fertig?")

## When NOT to use

- User gave full git command-line ("git add A B && git commit -m 'Y' && git push") — execute, don't inspect
- Single-purpose repo, clean tree, fresh-from-clone state — no ambiguity
- `git init`-from-scratch case (different concern, this skill assumes repo exists)
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
git status zeigt:
- 8 untracked hub-Files
- 5 untracked Subprojekt-Dirs (absprung/, pvista/, ...)
- 2 Mods in _shared/ und ops/
- 1 lokaler Commit ahead of origin/main

"Hub soll ins Repo" — meinst Du:
  A) NUR die 8 hub-Files + den ahead-Commit (Wolf-Intent vermutlich)
  B) hub + die 2 _shared/ops Mods auch
  C) Alle 5 Subprojekte zusätzlich (große Operation, vermutlich nicht heute)
```

Never assume A. Ask. The 60-Sekunden-Klärung verhindert eine 30-Minuten-Rollback.

## Real-world example: 2026-06-11 hub-commit

Wolf: „Der Hub soll ins Repo, kann am Schluss der aktuellen Session erfolgen"

**Without skill**: möglicher Pfad → lokales `~/Documents/Claude-Code/hub/` (nur Stub mit 2 Files) git-initialisieren, neuen GitHub-Repo erstellen, falsche Source pushen.

**Mit Inspektion**: aufgedeckt dass `/srv/projects/` auf swatserver bereits `Ed3Design/swatserver-infra` Mono-Repo ist mit:
- 1 ahead-Commit von 25.05. (`74ab162 feat(cockpit)`) → musste auch gepushed werden
- 8 untracked hub-Files (Dockerfile, compose, requirements, app/__init__.py, app/collectors.py, app/static/, app/templates/index.html, app/main.py — wait, main.py war tracked-modified)
- 2 OTHER modifications (`_shared/traefik`, `ops/postgres-dumpall.sh`) → NICHT committed (Scope-Klärung)
- 5 OTHER untracked Subprojekt-Dirs → NICHT committed (Scope-Klärung als Backlog vermerkt)

Outcome: 2 saubere Pushes (`74ab162` → `59ca63f`), keine Rollback, keine über-/unter-Commit-Drift.

## Quick-Reference

```bash
# 60-Sekunden-Inspektion vor jedem vagen Commit-Befehl:
git -C $PATH status --short
git -C $PATH log origin/$(git -C $PATH branch --show-current)..HEAD --oneline | head -5
git -C $PATH remote -v
# Dann User mit konkreten Scope-Optionen fragen.
```

## Anti-patterns

- ❌ **`git add .` ohne `git status` zu lesen** — fasst alle untracked Files inkl. Subdirs in den Commit
- ❌ **`git add -A` ohne Scope-Klärung** — stages auch _shared/ + ops/-Mods die der User nicht erwähnt hat
- ❌ **Annahme „User meinte das ganze Repo"** vs „User meinte nur EIN Subdir" — das ist GENAU die Ambiguität die diese Skill löst
- ❌ **Push vergessen** wenn `git log origin/main..HEAD` einen ahead-Commit zeigt — der bleibt sonst lokal verwaiste
- ❌ **Bei Sub-Dir-only Commit den Pfad-Prefix vergessen**: `git add Dockerfile` statt `git add hub/Dockerfile` → stage'd am Repo-Root, falscher Pfad
- ❌ **Mit `git commit -a` bei vagem Scope** — `-a` stage'd ALLE tracked-modified Files automatisch, übersteuert die Scope-Klärung
- ❌ **Submodules vergessen**: bei Submodule-Repos zusätzlich `git submodule status` checken, sonst landet ein Submodule-Pointer-Update versehentlich im Commit

## Special case: Mono-Repo mit untracked Subprojekten

Wenn `git status` zeigt `?? subproject-A/`, `?? subproject-B/`, ... als ganze Dirs:

**Frage explizit ab**:
> Untracked Subprojekte: `<list>`. Sollen die auch ins Mono-Repo, ODER sind das absichtlich separate Repos (lokal in `~/Documents/Claude-Code/<subproj>/`)?

Mono-Repo + separate Sub-Repos können koexistieren wenn `.gitignore` die Subprojekt-Dirs explizit excluded. Wenn die NICHT in `.gitignore` stehen aber dauerhaft untracked sind = unklare Strategie → Backlog-Item für eine Polish-Session.

## Connection to other skills

- `commit-message-honesty-precheck` (GA) — nach Scope-Klärung kommt die Commit-Message-Wahrheit
- `pre-push-bypass-audit-trail` (GA) — wenn Push trotzdem failed wegen Hook, vorher den Bypass-Audit
- `swatserver-fastapi-iteration` (GA) — sibling für swatserver-Deployment-Loop (rsync → docker compose → curl), kein Git
- `production-seed-vs-demo-seed-split` (GA) — bei Subprojekt-Klärung verwandt (wann seed-Files in Git vs gitignore'd)

## Promotion notes (DRAFT → GA)

Created 2026-06-11 from hub-commit session where Wolfs „Hub soll ins Repo" erst durch Inspektion korrekt scopebar wurde. Promote via `skill-tdd-promotion-workflow` after:
- 1 RED-Subagent: edge-cases wie „submodule changes", „rebase in progress (.git/MERGE_HEAD)", „shallow clone", „bare repo"
- 1 production-anchor real-world catch (z.B. ultimative-platform-Commit wo Scope nicht klar war zwischen Trader-Refactor und ML-Shadow-Items)
- Cross-link to `commit-message-honesty-precheck`
