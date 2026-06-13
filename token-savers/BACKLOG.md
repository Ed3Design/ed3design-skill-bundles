# Bundle-Backlog (token-savers)

## ⚠ Cycle-2 (Path-Refactor, blocking für externe Nutzer)

**Issue**: Skills referenzieren absolute Pfade `~/.claude/tools/X.py`. Bei Plugin-Install auf anderem System schlägt das fehl.

**Fix**: alle Skill-Pfade auf `${CLAUDE_PLUGIN_ROOT}/tools/X.py` umstellen. Betroffen:

- `image-preprocessing-helper/SKILL.md` — referenziert `~/.claude/tools/img-preprocess.py`
- `vault-search-helper/SKILL.md` — referenziert `~/.claude/tools/vault-search.py`
- `bash-output-filtering-disciplines/SKILL.md` — keine Tool-Refs (rein Pattern)
- `pdf-text-extract-without-vision/SKILL.md` — nutzt System-Binaries (`pdftotext`, `ocrmypdf`), keine Plugin-Pfade

Aufwand: ~15min sed-Replace + Verify.

## 📋 Andere Cycle-2-Items

1. **vault-search.py Config-Refactor**: `~/.config/vault-search/config.json` für Vault-Pfad (aktuell hartcoded `~/Documents/Vault/ClaudetteV/`)
2. **db-schema-inspector.py Config-Refactor**: `~/.config/db-schema-inspector/connections.json` für Connection-Profiles (aktuell hartcoded Wolf-Setup)
3. **html2md.py Optional-Deps**: `requirements.txt` für certifi + bs4 als install-time-Hint
4. **LICENSE-File** (MIT) hinzufügen
5. **Tests-Verzeichnis** mit Smoke-Tests pro Tool (CI-bereit)
6. **CONTRIBUTING.md** für externe Beiträge
7. **CI via GitHub-Actions**: pytest + lint + Bundle-Format-Validation

## 🎯 Pre-Publish-Checkliste

Bevor Plugin als Marketplace-Eintrag veröffentlicht werden kann:

- [ ] Path-Refactor (siehe oben)
- [ ] Tools-Config-Refactor (vault-search + db-schema-inspector)
- [ ] LICENSE-File
- [ ] CI-Tests grün
- [ ] README mit `/plugin install`-Befehl verifiziert
- [ ] Real-User-Test auf fremdem macOS-System
- [ ] Smoke-Test in Linux-Container

## 📊 Bundle-Status 2026-06-13

- ✅ Struktur (plugin.json + skills/ + tools/)
- ✅ 4 Skills kopiert (mit name-Field validiert)
- ✅ 5 Tools kopiert (executable + shebang)
- ✅ README mit empirischer Token-Saving-Tabelle
- ❌ Pfad-Refactor pending (Cycle-2 #1)
- ❌ GitHub-Repo `Ed3Design/ed3design-skill-bundles` noch nicht erstellt
- ❌ Marketplace-Submission pending
