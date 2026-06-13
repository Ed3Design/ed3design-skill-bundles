# code-quality

> Code-Quality + Git-Disziplinen — größtes Bundle (16 Skills). Sprach-/Framework-agnostisch.

## Skills (16) nach Sub-Domain

### Code-Review (4)

| Skill | Trigger |
|---|---|
| `code-review-backlog-cost-warning` | Backlog wächst → Review-Cost vs Inkrement-Cost |
| `code-review-chunk-dispatch` | >30 Commits Backlog → parallele Subagent-Chunks |
| `code-review-findings-als-red-tests` | Findings = Test-Cases → RED-Test pro Finding |
| `aggregate-code-review-after-tdd-tasks` | Multi-TDD-Task → ein Aggregat-Review |

### Git-Hygiene (3)

| Skill | Verhindert |
|---|---|
| `commit-message-honesty-precheck` | Subject lügt über Inhalt der Diff |
| `pre-push-bypass-audit-trail` | `--no-verify` ohne Audit-Eintrag |
| `cross-repo-state-inspection-before-commit` | Blind `add .` in Mono-Repo mit untracked Subdirs |

### Code-Patterns (5)

| Skill | Pattern |
|---|---|
| `cross-file-source-of-truth-grep` | DB-Spalten + Code-Refs cross-grep statt aus Erinnerung |
| `silent-except-versteckt-schema-drift` | `except: pass` versteckt Schema-Drift-Errors |
| `static-source-bug-class-coverage-test` | Bug-Klassen-Coverage via static grep |
| `library-subclass-explicit-type-classification` | Subclass-Typ explizit benennen, nicht implizit |
| `lazy-module-getattr-for-settings-override` | Module-Level-Freeze → Lazy-Read in Functions (env-Override wirkt) |

### Tooling (4)

| Skill | Wofür |
|---|---|
| `subprocess-ssh-arg-quoting-via-shlex` | SSH-Arg-Injection verhindern via shlex.quote |
| `bash-output-filtering-disciplines` | 12 Pattern-Katalog für Bash-Output-Triage |
| `ga-skill-edit-tdd-workflow` | GA-Skill editieren mit TDD-Cycle |
| `pytest-venv-first-triage` | venv-Aktivierung vor pytest-Triage |

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/code-quality/skills"/* ~/.claude/skills/
```

## Pattern-Compound

`cross-repo-state-inspection-before-commit` + `commit-message-honesty-precheck` + `pre-push-bypass-audit-trail` bilden eine **3-Layer-Git-Defense**: Scope-Klärung → Wahrheits-Subject → Bypass-Audit. Greift bei jedem `git push` für jedes Repo.

## Lizenz

MIT.
