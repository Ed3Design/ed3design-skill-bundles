# Bundle Backlog (token-savers)

## ✅ Cycle 2 done 2026-06-13

**Path refactor**: all skill paths migrated from `~/.claude/tools/X.py` to `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/X.py`. The **fallback pattern** (`:-$HOME/.claude`) means:

- Plugin install: `$CLAUDE_PLUGIN_ROOT` set → `<plugin-dir>/tools/`
- Locally installed skills: `$CLAUDE_PLUGIN_ROOT` unset → `$HOME/.claude/tools/`

→ Works in both contexts, no conflict with locally-installed skill catalogs.

Verification:
- `image-preprocessing-helper`: 7 replaces
- `vault-search-helper`: 4 replaces
- `bash-output-filtering-disciplines`: no tool refs (pattern-only skill)
- `pdf-text-extract-without-vision`: uses system binaries, no refs

## 📋 Other Cycle-2 Items

1. **vault-search.py config refactor**: `~/.config/vault-search/config.json` for vault path (currently hardcoded to a single vault location)
2. **db-schema-inspector.py config refactor**: `~/.config/db-schema-inspector/connections.json` for connection profiles (currently hardcoded sample setup)
3. **html2md.py optional deps**: `requirements.txt` for certifi + bs4 as install-time hints
4. **LICENSE file** per bundle (currently top-level only)
5. **Tests directory** with smoke tests per tool (CI-ready)
6. **CONTRIBUTING.md** for external contributions
7. **CI via GitHub Actions**: pytest + lint + bundle format validation

## 🎯 Pre-Publish Checklist

Before this bundle can be published to a marketplace:

- [x] Path refactor (done)
- [ ] Tools config refactor (vault-search + db-schema-inspector)
- [ ] LICENSE file
- [ ] CI tests green
- [ ] README with `/plugin install` command verified
- [ ] Real-user test on a fresh macOS system
- [ ] Smoke test in a Linux container

## 📊 Bundle Status 2026-06-13

- ✅ Structure (plugin.json + skills/ + tools/)
- ✅ 4 skills copied (name field validated)
- ✅ 5 tools copied (executable + shebang)
- ✅ README with empirical token saving table
- ✅ Path refactor (Cycle-2 #1)
- ❌ Tool config refactor pending
- ❌ Marketplace submission pending
