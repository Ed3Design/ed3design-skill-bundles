# ed3design-skill-bundles

> Engineering-Discipline-Bibliothek für Claude-Code-Power-User. 48 Skills + 5 Python-Tools in 6 thematischen Bundles.

## 📦 Bundles

| Bundle | Skills | Domain | Status |
|---|---|---|---|
| [`token-savers`](./token-savers/) | 4 + 5 Tools | Token-Optimierung (PDF/Image/Web/Vault/Schema/Diff) | ✅ PoC v0.1.0 + Path-Refactor done |
| [`code-quality`](./code-quality/) | 16 | Code-Review + Git-Hygiene + Code-Patterns | ✅ v0.1.0 |
| [`planning-disciplines`](./planning-disciplines/) | 10 | Roadmap + Decision + Reality-Inventur | ✅ v0.1.0 |
| [`async-forensik`](./async-forensik/) | 7 | asyncio + Container-Debugging | ✅ v0.1.0 |
| [`schema-discipline`](./schema-discipline/) | 6 | SQL/Schema-Bug-Class-Prevention | ✅ v0.1.0 |
| [`skill-system-meta`](./skill-system-meta/) | 5 | Skill-Lifecycle + Subagent-Patterns | ✅ v0.1.0 |

**Total**: 48 Skills + 5 Tools, ~67% des Wolf-Personal-Skill-Catalogs als generalisierte Bundles verfügbar.

## 🚀 Quickstart

```bash
# Clone repo
git clone https://github.com/Ed3Design/ed3design-skill-bundles
cd ed3design-skill-bundles

# Install one bundle (z.B. token-savers)
ln -s "$(pwd)/token-savers/skills"/* ~/.claude/skills/
cp token-savers/tools/*.py ~/.claude/tools/
chmod +x ~/.claude/tools/*.py

# Optional-Deps für token-savers
pip install certifi  # html2md SSL
brew install tesseract tesseract-lang poppler  # img-preprocess OCR + pdf-text-extract
```

Oder via Claude-Code-Marketplace (wenn registered):

```
/plugin install ed3design-skill-bundles/<bundle-name>
```

## 💡 Strategie hinter den Bundles

Diese Bundles entstanden aus **4 Wochen Wolf-Vault-Praxis** (Mai-Juni 2026) — alle Patterns sind empirisch in echten Trading/Maker/Engineering-Sessions gehärtet, nicht theoretisch konzipiert.

**Klassifikations-Quelle**: `02 Projekte/token-optimierung/skill-catalog-classification.md` im Wolf-Vault (~67% des 118-Skill-Catalogs als generalisierbar identifiziert).

**Pattern-Discovery**: jeder Skill durchläuft TDD-Promotion-Cycle (RED+GREEN-Subagent-Test) bevor er in einen Bundle aufgenommen wird. Siehe `skill-system-meta/skills/skill-tdd-promotion-workflow/`.

## 📐 Bundle-Format

Jeder Bundle hat:

```
<bundle-name>/
├── .claude-plugin/
│   └── plugin.json        # Claude-Code-Plugin-Manifest
├── skills/                # SKILL.md pro Skill (Frontmatter + Content)
│   └── <skill-name>/SKILL.md
├── tools/                 # Optional: Python-Helper-Scripts
└── README.md              # Bundle-Description + Trigger-Tabelle
```

**Portable Tool-Pfade**: Skills referenzieren Tools via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/X.py` — funktioniert sowohl im Plugin-Kontext als auch lokal installiert.

## 🔗 Verwandte Projekte

- [superpowers] von Jesse Vincent — Plugin-Format-Inspiration + TDD-für-Skills-Pattern
- [obsidian-vault] — viele Bundles entstanden aus Obsidian-Vault-Practice

## 📜 Lizenz

MIT. Patterns aus 4 Wochen Wolf-Praxis formalisiert.

## 🙏 Acknowledgements

Methodik aus dem [superpowers](https://github.com/obra/superpowers) Plugin-Ökosystem (Jesse Vincent). TDD-Promotion-Workflow + post-session-skill-review-Discipline aus Wolf-Vault-Practice.
