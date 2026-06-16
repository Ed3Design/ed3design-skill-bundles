---
name: production-seed-vs-demo-seed-split
description: |-
  Use when about to push a Code-Repo with seed/fixture-data containing real personal/customer/tenant data to a Remote (GitHub, GitLab) — even private. Triggers on phrases like "push repo for the first time", "create new private repo", "set up GitHub remote for <project>", "commit seed.py", "tenant data in code", "customer data in test data", "GDPR test data". Do NOT load for repos without personal data (pure tech repos like ESP32-firmware), for already-pushed repos (then it's git-filter-repo territory, different skill), or for ephemeral test-data without real-person reference. Encodes a property-management push-session pattern: 26 commits contained real tenant data + a .env demo credential; without the pre-push scan everything would have landed on GitHub.
---

> ✅ **PROMOTED** — TDD Cycle 1 **PASS (moderate)**. The RED-Subagent (without skill) reached almost all skill points heuristically from a privacy-boundary maxim, but sprawled across 9 steps with a self-hosting alternative. The GREEN-Subagent (with skill) delivered a focused 7 steps with a concrete real-name→WE-0001 mapping table + anti-pattern discipline ("delete instead of anonymize" is wrong). R1-Refactor applied: GDPR argument in history-rewrite, Option-A/B decision matrix, `.env.example` pattern, IBAN-dummy construction, commit-message audit command.

# Production-Seed vs Demo-Seed Split

When pushing a Code-Repo for the first time, the seed/fixture data is often the leakiest surface. Personal data (names, addresses, tenancy details, customer numbers) in `seed.py` or fixtures lands in the Git-History, which lives on the Remote forever — even on private repos.

## The 4-step pattern

### Step 1: Scan for personal-data shape
```bash
# Which files are seed/fixture candidates?
git ls-files | grep -iE "seed|fixture|sample|demo|test_data"

# Real names + sensitive patterns in the working tree
git grep -lE "(<known-real-names>|@\w+\.(de|com)|@gmail|birth|address|tax|IBAN)" -- seed.py fixtures/

# Scan commit messages too (they get pushed!)
git log --all --pretty=format:"%s %b" | grep -iE "<known-real-names>|@\w+\.(de|com)"

# Is .env tracked?
git ls-files | grep -E "^\.env$|\.env\."

# Migration files with data inserts (a common anti-pattern with Alembic/Django)?
git ls-files | grep -E "(migrations|versions)/.*\.py$" | xargs grep -lE "INSERT|insert\(" 2>/dev/null
```
If matches: **STOP — proceed to step 2 before any push**.

### Step 2: Backup real seed to gitignored file
```bash
cp seed.py seed_real.py  # real data stays for the local production DB
```

### Step 3: Anonymize seed.py in-place
Replace real names with structural IDs:
- `<real-name-1>` → `Tenant unit WE-0007`
- `<real-name-2>` → `Tenant unit WE-0006`
- `<real-name-3>` → `Tenant unit WE-0002`
- `<real-role-title>` → `Contact person Customer-0042`

**IBAN dummies** — pick a syntactically invalid one so there is no risk of accidental real use:
- ❌ `DE89 3704 0044 0532 0130 00` (classic demo IBAN, syntactically valid → can be checked against reality)
- ✅ `DE00 0000 0000 0000 0000 00` (check digits 00 are invalid)
- ✅ `DE99 0000 0000 0000 0000 99` (check digits 99 are invalid)

**Round real amounts**: `847.32 EUR` → `850 EUR` (demo values, no inference about real conditions).

Add a banner docstring to seed.py explaining that the real seed lives in seed_real.py:

```python
"""
Demo seed for CI/tests/public structure.
Real tenant data lives locally in seed_real.py (gitignored).
NEVER put real names, IBAN, dates of birth or addresses in this file.
"""
```

Verify: `git grep -iE "real-name-1|real-name-2|..." seed.py` must be empty.

### Step 4: Update .gitignore + .env + commit
```
# Sensitive production data
backend/seed_real.py
backend/seed_production.py
backend/seed_data/production.*

# Local env (never track)
.env
.env.local
!.env.example

# DB files with production data
*.db
*.sqlite
*.sqlite3
backend/*.db
```

**`.env.example` pattern** (standard convention):
```bash
# .env.example is committed, .env is not
cat > .env.example <<EOF
DB_URL=sqlite:///./app.db
SECRET_KEY=changeme
EOF
git add .env.example
```

If `.env` was already tracked in the 26 commits:
```bash
git rm --cached .env  # exclude from future commits
# the history check in Step 5 decides whether SECRET_KEY must be rotated
```

Commit as `chore: anonymize seed.py + .gitignore seed_real.py + untrack .env (pre-push hygiene)`.

## History-Rewrite Entscheidungsmatrix

Anonymize-forward is NOT enough when the history already contains real PII — the old commits live on in the repo. For GDPR-relevant data (tenants, patients, employees, customers), "private to me" is not legally sufficient, because as the controller (GDPR Art. 4(7)) you have **no legal basis** to store this data on GitHub servers (Microsoft Ireland) — not even in private history.

| Situation | Recommendation | Rationale |
|---|---|---|
| Solo dev + **not yet pushed** + GDPR data | **Option A — `git filter-repo`** | No force-push conflict, no broken clones, GDPR-compliant (data minimization Art. 5) |
| Solo dev + already-pushed + GDPR data | **Option A + force push** + inform data subjects? | Tricky: old refs on GitHub servers may stay archived for months. Last resort: delete repo + recreate |
| Solo dev + not yet pushed + NO GDPR data | **Option A or B by time budget** | Filter-repo is worthwhile for hygiene, but is not a mandatory step |
| Team repo + already-pushed | **Option B (forward-clean)** + collaborator coordination | Filter-repo breaks forks, force-push is socially unreasonable |
| Repo with < 5 commits | **Option A or recreate** | Cost-benefit is unambiguous |

**Option A — `git filter-repo`** (nuclear, but clean):
```bash
pip install git-filter-repo
# back up first
cp -r .git ../<project>-git-backup

# Variant 1: rewrite the seed.py path entirely out of history
git filter-repo --path backend/seed.py --invert-paths
# then re-add the anonymized seed.py + initial commit

# Variant 2: replace-text for targeted name replacements
# expressions.txt with "<real-name>==>Tenant unit WE-0001" etc.
git filter-repo --replace-text expressions.txt
```

**Option B — Forward-clean + accept history** (ONLY without GDPR data or with data-subject consent):
- Push as-is, repo privacy as the boundary
- Document in the chore commit that the history pre-anonymization contains real data

**Alternative C — Self-host instead of GitHub**: for a purely private tool a Tailscale-only Gitea on your own server is, in data-protection terms, clearer than "GitHub private". No data-processing agreement needed, the server stays in your own sphere.

## Anti-patterns

- ❌ Push first, anonymize later — the data is then irrevocably in the remote history
- ❌ Relying on "a private repo already protects" — GitHub employee access, org-add risk, compromise scenarios
- ❌ Deleting seed.py instead of anonymizing — the app needs structural data for demo/CI
- ❌ Real names in commit messages — these get pushed too and are just as visible as code

## Real-world impact

**Property-management app**: Before the pre-push scan: 26 commits with 16 lines of plaintext tenant data + a tracked `.env`. After the 4-step pattern: anonymized + gitignored, clean forward push. Pushback discipline upheld ("`backend/seed.py` contains REAL tenant data" flagged as HIGH risk before push).

## Background: TDD log (bulletproofing log)

### Cycle 1 (PASS moderate with R1-Refactor)

- **RED-Subagent** (without skill, scenario "push a property-management app for the first time, 26 commits, seed.py with real names/IBAN"): Reached almost all skill points heuristically from experience + a privacy-boundary maxim: inventory, seed audit, production-vs-demo split, .gitignore, history check, .env rotation, README, GitHub settings, 2FA, self-hosting alternative. **9 steps**, very broad, with a sprawling self-critique (8 unverified assumptions). Added value: **GDPR Art. 6/Art. 9 reasoning** + data-processing-agreement note + Tailscale self-host alternative. But the answer felt "scattered" — no clear path.

- **GREEN-Subagent** (with skill, same prompt): A focused **7-step path** along the 4-step pattern + history-rewrite recommendation (Option A justified for an empty remote). Concrete mapping table real-name→WE-0001, IBAN-dummy note (DE89 is syntactically valid → risk), anti-pattern "delete instead of anonymize" explicit. Self-reflection identified 5 skill gaps: (1) GDPR argument missing from "Why not history-rewrite?", (2) Option-A/B decision matrix missing, (3) `.env.example` pattern missing, (4) IBAN-dummy construction missing, (5) commit-message audit missing from Step 1.

- **Value class**: Unlike `enum-known-values-via-insert-grep` (where GREEN found real bugs RED missed), here the skill value lies in **focus + a reproducible mapping table + anti-pattern discipline**. RED's answer would be meaningful for an experienced reader, but not scalable / not repeatable.

- **R1-Refactor applied** (all 5 gaps from GREEN self-reflection):
  - **R1.1**: GDPR Art. 4(7) + Art. 5 reasoning built into the "History-Rewrite decision matrix"
  - **R1.2**: Decision matrix with 5 situations × 2 options + Alternative C (self-host) added
  - **R1.3**: `.env.example` pattern documented in Step 4 as a standard convention + cat-heredoc example
  - **R1.4**: IBAN-dummy construction in Step 3 with ❌/✅ examples (the DE89 trap → invalid check digits 00/99)
  - **R1.5**: commit-message audit + migration-insert audit commands added to Step 1

### Cycle-2 backlog (polish, non-blocking)

1. **Example listing per repo size**: 5/20/100-commit repos with a concrete Option-A-vs-B verdict
2. **Test-snapshot pattern**: pytest fixtures that copy real data as "realistic tests" is a common anti-pattern — add its own sub-step
3. **Post-push success verification**: `gh secret scanning list` command + audit-log path for GitHub settings
4. **Cross-skill reference**: to `pre-push-bypass-audit-trail` (already exists) — its audit log should also capture pre-push seed scans
5. **Self-host "Gitea" setup skill**: a separate skill, if the self-host variant is used regularly
