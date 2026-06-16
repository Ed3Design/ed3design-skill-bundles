# code-quality

> Code-quality + Git discipline skills — the largest bundle (21 skills + 4 hooks + 1 agent). Language-/framework-agnostic.

## Skills (16) by sub-domain

### Code Review (4)

| Skill | Trigger |
|---|---|
| `code-review-backlog-cost-warning` | Backlog grows → review cost vs. increment cost |
| `code-review-chunk-dispatch` | >30 commits backlog → parallel sub-agent chunks |
| `code-review-findings-als-red-tests` | Findings = test cases → RED test per finding |
| `aggregate-code-review-after-tdd-tasks` | Multi-TDD task → one aggregate review |

### Git Hygiene (3)

| Skill | Prevents |
|---|---|
| `commit-message-honesty-precheck` | Subject lies about content of the diff |
| `pre-push-bypass-audit-trail` | `--no-verify` without audit entry |
| `cross-repo-state-inspection-before-commit` | Blind `add .` in mono-repo with untracked subdirs |

### Code Patterns (5)

| Skill | Pattern |
|---|---|
| `cross-file-source-of-truth-grep` | DB columns + code refs cross-grep instead of from memory |
| `silent-except-hides-schema-drift` | `except: pass` hides schema-drift errors |
| `static-source-bug-class-coverage-test` | Bug class coverage via static grep |
| `library-subclass-explicit-type-classification` | Name subclass type explicitly, not implicitly |
| `lazy-module-getattr-for-settings-override` | Module-level freeze → lazy read in functions (env override works) |

### Tooling (4)

| Skill | Purpose |
|---|---|
| `subprocess-ssh-arg-quoting-via-shlex` | Prevent SSH arg injection via shlex.quote |
| `bash-output-filtering-disciplines` | 12-pattern catalog for bash-output triage |
| `ga-skill-edit-tdd-workflow` | Edit GA skill with TDD cycle |
| `pytest-venv-first-triage` | venv activation before pytest triage |

## 🪝 Hooks (4) — Automatic enforcement

Active after plugin install via `hooks/hooks.json`. PreToolUse on bash commands:

| Hook | Trigger | Behavior |
|---|---|---|
| `cross-repo-state-inspect.sh` | `git add .` / `git add -A` / `git commit -a` | Warns against blind-add in mono-repos |
| `commit-message-honesty.sh` | `git commit -m "<generic>"` | Warns on WIP/update/misc/various subjects |
| `pre-push-bypass-audit.sh` | `git push --no-verify` etc. | Audit log + warning |
| `pytest-venv-first.sh` | direct `pytest` call | Warns if venv not active but `.venv/` exists |

All hooks: **warn-only (exit 0)**, no block. Stderr messages land in the Claude context → subsequent tool calls see the warning.

## 🤖 Sub-Agent (1)

| Agent | Description |
|---|---|
| `code-reviewer` | Read-only sub-agent. 5 mandatory lenses (convention, silent-failure, hardcoded defaults, cross-file consistency, commit honesty). Sonnet model, tools: Read+Grep+Glob+Bash |

Dispatch via:
```python
Agent(subagent_type="general-purpose", description="Code-Review Range X", prompt="Load via Skill tool the agent 'code-quality:code-reviewer' and follow its instructions for git diff HEAD~5..HEAD")
```

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/code-quality/skills"/* ~/.claude/skills/
```

## Pattern Compound

`cross-repo-state-inspection-before-commit` + `commit-message-honesty-precheck` + `pre-push-bypass-audit-trail` form a **3-layer Git defense**: scope clarification → truthful subject → bypass audit. Triggers on every `git push` for every repo.

## License

MIT.
