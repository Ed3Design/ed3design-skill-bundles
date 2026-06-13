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

## 🪝 Hooks (4) — Automatische Enforcement

Aktiv nach Plugin-Install via `hooks/hooks.json`. PreToolUse auf Bash-Commands:

| Hook | Trigger | Verhalten |
|---|---|---|
| `cross-repo-state-inspect.sh` | `git add .` / `git add -A` / `git commit -a` | Warnt vor blind-add in Mono-Repos |
| `commit-message-honesty.sh` | `git commit -m "<generic>"` | Warnt bei WIP/update/misc/various Subjects |
| `pre-push-bypass-audit.sh` | `git push --no-verify` etc. | Audit-Log + Warnung |
| `pytest-venv-first.sh` | direkter `pytest`-Aufruf | Warnt wenn venv nicht aktiv aber `.venv/` vorhanden |

Alle Hooks: **warn-only (exit 0)**, kein Block. Stderr-Messages landen im Claude-Context → künftige Tool-Calls sehen die Warnung.

## 🤖 Sub-Agent (1)

| Agent | Beschreibung |
|---|---|
| `code-reviewer` | Read-only Subagent. 5 Pflicht-Linsen (Convention, Silent-Failure, Hardcoded-Defaults, Cross-File-Consistency, Commit-Honesty). Sonnet-Modell, Tools: Read+Grep+Glob+Bash |

Dispatch via:
```python
Agent(subagent_type="general-purpose", description="Code-Review Range X", prompt="Lies via Skill-Tool den Agent 'code-quality:code-reviewer' und folge dessen Anweisungen für git diff HEAD~5..HEAD")
```

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/code-quality/skills"/* ~/.claude/skills/
```

## Pattern-Compound

`cross-repo-state-inspection-before-commit` + `commit-message-honesty-precheck` + `pre-push-bypass-audit-trail` bilden eine **3-Layer-Git-Defense**: Scope-Klärung → Wahrheits-Subject → Bypass-Audit. Greift bei jedem `git push` für jedes Repo.

## Lizenz

MIT.
