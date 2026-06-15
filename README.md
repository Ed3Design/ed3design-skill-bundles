# ed3design-skill-bundles

[![Bundle Validation](https://github.com/Ed3Design/ed3design-skill-bundles/actions/workflows/validate.yml/badge.svg)](https://github.com/Ed3Design/ed3design-skill-bundles/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Software-engineering-discipline library for Claude Code power users. 47 skills + 5 Python tools + 6 hooks + 4 sub-agents across 6 thematic bundles.

## 📦 Bundles (Software Engineering)

| Bundle | Skills | Hooks | Agents | Tools | Status |
|---|---|---|---|---|---|
| [`token-savers`](./token-savers/) | 3 | **1** | — | 5 | ✅ v0.2.0 |
| [`code-quality`](./code-quality/) | 16 | **4** | **1** (`code-reviewer`) | — | ✅ v0.2.0 |
| [`planning-disciplines`](./planning-disciplines/) | 10 | — | **1** (`planning-assistant`) | — | ✅ v0.2.0 |
| [`async-forensik`](./async-forensik/) | 7 | — | **1** (`forensik-detective`) | — | ✅ v0.2.0 |
| [`schema-discipline`](./schema-discipline/) | 6 | — | **1** (`schema-validator`) | — | ✅ v0.2.0 |
| [`skill-system-meta`](./skill-system-meta/) | 5 | **1** | — | — | ✅ v0.2.0 |

**Total**: 47 skills + 6 hooks + 4 sub-agents + 5 tools — patterns extracted from real-world software engineering practice and structured for reuse (Python/SQL/Git workflows).

## 🔧 Hardware / Maker Engineering — Separate Repo

Hardware-focused bundles (parametric CAD, FDM/maker workflows, embedded systems) moved to a **dedicated sibling repo** for clearer audience differentiation:

→ **[`ed3design-engineering-bundles`](https://github.com/Ed3Design/ed3design-engineering-bundles)** — 8 skills across 3 bundles (cad-design, maker-fdm, embedded-systems). Public, MIT licensed.

For makers, mechanical engineers, embedded hobbyists. Includes the Fusion 360 MCP-Bridge skill for Claude-driven CAD automation and the Victron Cerbo Modbus device-onboarding skill (encodes the non-obvious `Enabled=0` default).

## 🚀 Quickstart

### Via Claude Code Marketplace (Recommended)

Add this repo as a marketplace, then install bundles individually:

```
/plugin marketplace add Ed3Design/ed3design-skill-bundles
/plugin install token-savers@ed3design-skill-bundles
/plugin install code-quality@ed3design-skill-bundles
# ... or any of the 6 bundles
```

Available plugins after `marketplace add`:
- `token-savers` — Token optimization (3 skills + 5 tools)
- `code-quality` — Code review + Git hygiene (16 skills + 4 hooks + 1 agent)
- `planning-disciplines` — Roadmap + decision (10 skills + 1 agent)
- `async-forensik` — asyncio + container debugging (7 skills + 1 agent)
- `schema-discipline` — SQL/schema bug prevention (6 skills + 1 agent)
- `skill-system-meta` — Skill lifecycle (5 skills + 1 hook)

### Manual install (no marketplace)

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
cd ed3design-skill-bundles

# Install one bundle (e.g. token-savers)
ln -s "$(pwd)/token-savers/skills"/* ~/.claude/skills/
cp token-savers/tools/*.py ~/.claude/tools/
chmod +x ~/.claude/tools/*.py

# Optional dependencies (token-savers):
pip install certifi              # html2md SSL
brew install tesseract tesseract-lang poppler  # OCR + PDF
```

## 💡 Design Philosophy

These bundles emerged from intensive engineering practice — every pattern is empirically hardened in real software engineering sessions, not theoretically designed.

**Pattern Discovery Methodology**: each skill goes through a TDD-promotion cycle (RED + GREEN sub-agent test) before being added to a bundle. See `skill-system-meta/skills/skill-tdd-promotion-workflow/`.

**Generalization Criterion**: a skill is bundled only if it's cross-domain useful — independent of specific projects, business domains, or proprietary infrastructure. Project-specific patterns stay in the original catalog.

## 📐 Bundle Format

Each bundle follows the Claude Code plugin convention:

```
<bundle-name>/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── skills/                  # SKILL.md per skill (frontmatter + content)
│   └── <skill-name>/SKILL.md
├── hooks/                   # Optional: PreToolUse/Stop/UserPromptSubmit hooks
│   ├── hooks.json
│   └── <hook-name>.sh
├── agents/                  # Optional: custom sub-agent definitions
│   └── <agent-name>.md
├── tools/                   # Optional: Python helper scripts
└── README.md                # Bundle description + trigger table
```

**Portable Tool Paths**: skills reference tools via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/X.py` — works both in the plugin context and locally installed.

## 🔗 Related Projects

- [superpowers](https://github.com/obra/superpowers) by Jesse Vincent — plugin format inspiration + TDD-for-skills pattern

## 📜 License

MIT.

## 🙏 Acknowledgements

Methodology draws from the [superpowers](https://github.com/obra/superpowers) plugin ecosystem (Jesse Vincent). The TDD-promotion-workflow + post-session-skill-review discipline emerged from sustained practice.
