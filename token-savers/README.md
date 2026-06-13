# token-savers

> Token-Optimierung-Bundle für Claude-Code. 4 Skills + 5 Python-Tools mit empirisch belegten 70-98% Saving-Raten.

## 📊 Empirische Token-Saving-Empirik (12.-13.06.2026)

| Workflow | Vorher | Nachher | Saving | Tool/Skill |
|---|---|---|---|---|
| PDF-Read 20 Seiten | ~100k Vision-Tokens | ~12k Text-Tokens | **~85%** | `pdf-text-extract-without-vision` |
| Image-Vision (4032×3024 iPhone) | ~10k Tokens | ~1.2k Tokens | **~88%** | `image-preprocessing-helper` |
| Vault-First-Check (5 Calls) | ~14k Tokens | ~3.5k Tokens | **~75%** | `vault-search-helper` |
| `\d table` Schema-Verify | ~1500 Tokens | ~30 Tokens (compact) | **~98%** | `db-schema-inspector.py` |
| `git diff --stat HEAD~5..HEAD` | ~2-5k Tokens | ~600 Tokens | **~75%** | `diff-summary.py` |
| Wikipedia-Article-Read | ~92k Tokens | ~1.5k Tokens | **~98%** | `html2md.py` |
| `docker logs` Filter | ~3-5k Tokens | ~300 Tokens | **~85%** | `bash-output-filtering-disciplines` |

## 🛠 Was ist drin

### Skills (4)

- **`pdf-text-extract-without-vision`** — `pdftotext` (poppler) oder OCR-Fallback (`ocrmypdf`) statt Claude Vision für PDFs
- **`image-preprocessing-helper`** — resize/ocr/info/colors via lokales Python-Tool vor Vision-Call
- **`vault-search-helper`** — Single-Call ranked Search statt mehrere Glob+Grep
- **`bash-output-filtering-disciplines`** — 12 Pattern-Katalog-Items für Bash-Output-Triage (head, tail, grep, jq, awk Patterns)

### Tools (5 Python-Skripte)

- **`img-preprocess.py`** — PIL-basiert. Sub-Commands: resize/ocr/info/colors/describe
- **`vault-search.py`** — Multi-Word-Query + Score-Heuristik + Top-N JSON-Output
- **`db-schema-inspector.py`** — `information_schema.columns` via ssh+docker exec oder direkt psql. JSON-Output, compact-mode
- **`diff-summary.py`** — `git diff --numstat` + Change-Type-Klassifikation (refactor/feat/fix/test/migration)
- **`html2md.py`** — bs4 content-extraction + Markdown-Konvertierung. certifi-SSL (best-practice), kein insecure-Fallback

## 🚀 Installation

```bash
# Als Plugin via marketplace (Claude-Code Setting)
/plugin install ed3design-skill-bundles/token-savers

# Oder manuell:
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/token-savers/skills"/* ~/.claude/skills/
cp ed3design-skill-bundles/token-savers/tools/*.py ~/.claude/tools/
chmod +x ~/.claude/tools/*.py

# Optional-Deps für volle Funktionalität:
pip install certifi  # html2md SSL
brew install tesseract tesseract-lang  # img-preprocess OCR
brew install poppler  # pdf-text-extract
```

## 💡 Trigger-Patterns

| User-Phrase | Skill/Tool das triggert |
|---|---|
| „schau dir das Screenshot an" | `image-preprocessing-helper` |
| „PDF lesen" / „aus PDF extrahieren" | `pdf-text-extract-without-vision` |
| „Vault-First-Check zu X" | `vault-search-helper` |
| „Schema-Verify für Tabelle X" | `db-schema-inspector.py` |
| „was hat sich seit X geändert?" | `diff-summary.py` |
| „lies diese Webseite" | `html2md.py` |
| „docker logs zeigt zu viel" | `bash-output-filtering-disciplines` |

## 📐 Design-Prinzipien

1. **Lokale Tool-Ausführung > Vision-API** wo möglich. Vision nur wenn semantisches Bildverständnis nötig.
2. **Pre-Processing statt Raw-Input** in Context. 90% des HTML/PDF/Screenshot-Inhalts ist Boilerplate.
3. **Best-Practice-Security**: certifi statt `verify=False`. Klare Setup-Errors bei Missing-Deps statt Insecure-Fallback.
4. **Strukturierter JSON-Output** statt Raw-Text wo möglich. Spart Tokens beim weiteren Reasoning.
5. **Single-Source-of-Truth**: Tools sind Wrapper um stdlib + 1-2 well-tested Libs (PIL, bs4, certifi). Kein eigenes HTML-Parsing oder PDF-Extraction.

## 🔗 Verwandte Bundles (Roadmap)

- `code-quality` — 16 Skills für Code-Review + Git-Disziplin
- `schema-discipline` — 6 Skills für SQL/Schema-Patterns
- `async-forensik` — 7 Skills für asyncio + Container-Debugging
- `planning-disciplines` — 10 Skills für Roadmap + Decision-Making
- `skill-system-meta` — 5 Skills für Skill-Building selbst

## 📜 Lizenz

MIT. Pattern-Empirik aus Wolfs Trading + Maker + Vault-Praxis. Beitrag willkommen — siehe [CONTRIBUTING.md] (kommt).

## 🙏 Acknowledgements

Pattern-Discovery-Methodik aus dem [superpowers] Plugin-Ökosystem (Jesse Vincent). TDD-Promotion-Workflow + post-session-skill-review-Discipline aus 4 Wochen Wolf-Practice formalisiert.
