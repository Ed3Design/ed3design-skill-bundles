# token-savers

> Token optimization bundle for Claude Code. 4 skills + 5 Python tools with empirically measured 70-98% savings.

## 📊 Empirical Token Savings

| Workflow | Before | After | Saving | Tool/Skill |
|---|---|---|---|---|
| PDF read (20 pages) | ~100k vision tokens | ~12k text tokens | **~85%** | `pdf-text-extract-without-vision` |
| Image vision (4032×3024) | ~10k tokens | ~1.2k tokens | **~88%** | `image-preprocessing-helper` |
| Vault search (5 calls) | ~14k tokens | ~3.5k tokens | **~75%** | `vault-search-helper` |
| `\d table` schema verify | ~1500 tokens | ~30 tokens (compact) | **~98%** | `db-schema-inspector.py` |
| `git diff --stat HEAD~5..HEAD` | ~2-5k tokens | ~600 tokens | **~75%** | `diff-summary.py` |
| Wikipedia article read | ~92k tokens | ~1.5k tokens | **~98%** | `html2md.py` |
| `docker logs` filter | ~3-5k tokens | ~300 tokens | **~85%** | `bash-output-filtering-disciplines` |

## 🛠 Contents

### Skills (4)

- **`pdf-text-extract-without-vision`** — `pdftotext` (poppler) or OCR fallback (`ocrmypdf`) instead of Claude Vision for PDFs
- **`image-preprocessing-helper`** — resize/ocr/info/colors via local Python tool before vision call
- **`vault-search-helper`** — single-call ranked search instead of multiple Glob+Grep
- **`docx-tab-position-extraction-for-layout-replication`** — extract tab-stop positions from a Word `.docx` to replicate its layout in HTML/CSS/PDF/Print-CSS

For bash-output filtering disciplines (head, tail, grep, jq, awk patterns), see the `code-quality` bundle.

### Tools (5 Python scripts)

- **`img-preprocess.py`** — PIL-based. Sub-commands: resize/ocr/info/colors/describe
- **`vault-search.py`** — multi-word query + score heuristic + top-N JSON output
- **`db-schema-inspector.py`** — `information_schema.columns` via ssh+docker exec or direct psql. JSON output, compact mode
- **`diff-summary.py`** — `git diff --numstat` + change-type classification (refactor/feat/fix/test/migration)
- **`html2md.py`** — bs4 content extraction + Markdown conversion. certifi SSL (best-practice), no insecure fallback

## 🚀 Installation

```bash
# Via marketplace:
/plugin marketplace add Ed3Design/ed3design-skill-bundles
/plugin install token-savers@ed3design-skill-bundles

# Or manually:
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/token-savers/skills"/* ~/.claude/skills/
cp ed3design-skill-bundles/token-savers/tools/*.py ~/.claude/tools/
chmod +x ~/.claude/tools/*.py

# Optional dependencies for full functionality:
pip install Pillow              # img-preprocess (required for resize/info/describe)
pip install beautifulsoup4      # html2md (required for content extraction)
pip install certifi             # html2md SSL (recommended for macOS/Python.org)
# or in one shot from the bundle repo root:
#   pip install '.[token-savers]'

# System binaries (optional, for OCR + PDF):
brew install tesseract tesseract-lang  # img-preprocess OCR mode
brew install poppler            # pdf-text-extract
```

## 💡 Trigger Patterns

| User phrase | Skill/tool triggered |
|---|---|
| "look at this screenshot" | `image-preprocessing-helper` |
| "read this PDF" / "extract from PDF" | `pdf-text-extract-without-vision` |
| "vault-first check for X" | `vault-search-helper` |
| "schema verify for table X" | `db-schema-inspector.py` |
| "what changed since X?" | `diff-summary.py` |
| "read this webpage" | `html2md.py` |
| "docker logs too verbose" | `bash-output-filtering-disciplines` |

## 📐 Design Principles

1. **Local tool execution > Vision API** where possible. Vision only when semantic image understanding is required.
2. **Pre-processing instead of raw input** in context. 90% of HTML/PDF/screenshot content is boilerplate.
3. **Security best-practice**: certifi instead of `verify=False`. Clear setup errors on missing deps instead of insecure fallback.
4. **Structured JSON output** instead of raw text where possible. Saves tokens on downstream reasoning.
5. **Single source of truth**: tools are wrappers around stdlib + 1-2 well-tested libs (PIL, bs4, certifi). No custom HTML parsing or PDF extraction.

## 🔗 Related Bundles

- `code-quality` — 21 skills for code-review + Git discipline
- `schema-discipline` — 8 skills for SQL/schema patterns
- `async-forensik` — 8 skills for asyncio + container debugging
- `planning-disciplines` — 10 skills for roadmap + decision-making
- `skill-system-meta` — 5 skills for skill-building itself

## 📜 License

MIT.
