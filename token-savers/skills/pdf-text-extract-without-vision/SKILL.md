---
name: pdf-text-extract-without-vision
description: Use BEFORE reading any PDF file when the goal is to extract textual content (specs, contracts, articles, manuals, financial reports, legal documents). STOP and run `pdftotext` from the poppler-utils package locally instead of letting Claude read the PDF directly. Claude Vision burns 1-5k tokens per page even for text-heavy PDFs that are 100% mechanically extractable. `pdftotext` is a free local CLI tool (already installed at /opt/homebrew/bin/pdftotext, version 26.04.0+ for poppler v26+) that converts PDF text-layer to plain UTF-8 markdown-ish text at zero token cost. Trigger on phrases like "lies dieses PDF", "extrahiere Text aus dem PDF", "was steht in der PDF", "fasse die PDF zusammen", "PDF analysieren", "PDF-Inhalt zeigen", "Text aus dem Dokument holen", "Spec aus PDF lesen", "Vertrag aus PDF auswerten", "Manual auswerten", any user request involving "PDF" + content-comprehension. Do NOT use for image-only PDFs (scans without OCR'd text-layer — pdftotext returns empty; fallback to Claude Vision OR run `ocrmypdf` first), for PDFs where the LAYOUT is the primary information (architectural drawings, design mockups, infographics — there the visual structure matters), for PDFs less than ~1 page where token cost is negligible (~500 tokens total), or for PDFs that contain critical embedded images Claude must SEE not READ (charts where the trend-shape matters more than the data-table). Encodes Wolf's Token-Optimization-Session 11.06.2026 finding: Claude Vision for typical text-heavy PDFs (specs, manuals, financial reports) is 5-20x more expensive than pdftotext + Read tool — directly violates Brain-Dump-Token-Optimierungs-Direktive from 05.06.
---

# PDF-Text-Extract without Vision

> ✅ **PROMOTED 2026-06-12** via TDD-Cycle (RED+GREEN-Subagent-Pair). RED-Subagent reflektierte selbst „mein Default-Approach (direkter Read mit pages-Param) ist suboptimal" — Skill verhindert genau diese Default-Vision-Falle. GREEN-Subagent erreichte ~90% Token-Reduktion mit `-layout` bewusst gewählt für Tabellen-Datenblatt.

## Overview

Wolf-Brain-Dump-Item (05.06.2026): *„kritische Analyse der Token-Nutzung — eigene Tools (zum Beispiel pdf oder img per Python anstatt Claude in Txt umwandeln)"*

Claude Vision verarbeitet jede PDF-Seite als Bild → **1-5k Tokens pro Seite** auch bei reinen Text-PDFs. Bei 20-seitigen Specs = 20-100k Tokens **nur fürs Lesen**, bevor irgendetwas analysiert wurde. Komplett vermeidbar wenn das PDF eine Text-Layer hat (gilt für ~95% aller modernen PDFs).

`pdftotext` aus `poppler-utils` (lokal auf macOS via Homebrew installiert) extrahiert die Text-Layer in **0 Tokens** Server-Cost und gibt Plain-Text zurück, den Claude per `Read`-Tool effizient liest.

## When to Trigger

✅ **JA — pdftotext-first:**
- User sagt „lies dieses PDF" / „PDF zusammenfassen" / „Spec aus PDF"
- PDF im Vault unter `07 Anhänge/` oder als externer Pfad referenziert
- PDF kommt aus offiziellen Quellen (BGH, Notar, Behörden, Manuals, Whitepapers, ML-Papers)
- > 2 Seiten **oder** Text-fokussierter Content

❌ **NEIN — Vision behalten:**
- PDF ist gescanntes Original (kein Text-Layer) → erst `ocrmypdf` laufen lassen, dann pdftotext
- Layout/Visuals sind die Information (Architektur-Pläne, Mockups, Charts wo Trend-Shape wichtiger ist als Zahlen)
- Sehr kleine PDFs (1 Seite, ~500 Tokens) wo Setup-Overhead nicht lohnt
- PDF enthält kritische eingebettete Diagramme die Claude SEHEN soll, nicht lesen

## Steps

### Step 0: Metadaten-Probe (Seitenzahl + Größe verifizieren)

User-Behauptungen über PDFs („20 Seiten Spec", „nur 1 Seite") sind oft falsch. Vor Approach-Wahl verifizieren:

```bash
pdfinfo "/path/to/doc.pdf" | grep -E "Pages|File size|Page size"
# Pages:           1
# File size:       244532 bytes
# Page size:       612 x 792 pts (letter)
```

Wenn `Pages: 1` → Token-Cost auch für Vision-Direct gering (~2-5k), Skill-Setup-Overhead lohnt eventuell nicht. Bei `Pages: >5` → Skill klar lohnen. Bei `Pages: 20+` → MUST-USE.

### Step 1: Pfad-Check + Text-Layer-Probe

```bash
# Check Tool verfügbar
which pdftotext || brew install poppler

# Quick-Probe: hat das PDF eine Text-Layer?
pdftotext -nopgbrk "/path/to/doc.pdf" - | head -20
```

Wenn Output leer / nur Whitespace → PDF ist scan-basiert, fallback zu OCR (siehe Step 4) oder Vision.

### Step 2: Voll-Extraktion in Temp-File

```bash
# Standard-Variante: ein flacher Text-File
pdftotext -nopgbrk "/path/to/doc.pdf" /tmp/extracted.txt

# Layout-aware Variante (bei Tabellen / mehrspaltigen Texten):
pdftotext -layout "/path/to/doc.pdf" /tmp/extracted-layout.txt

# Mit Seitenzahlen als Header (bei langen Specs hilfreich):
pdftotext "/path/to/doc.pdf" -  # default: form-feed \f als Seitentrenner
```

**Flag-Tipps:**
- `-nopgbrk`: keine `\f`-Seitentrennung (flacher Text)
- `-layout`: erhält Tabellen-Struktur (Spalten via Whitespace)
- `-raw`: keep original text-order (für komplexe Layouts manchmal besser)
- `-f N -l M`: nur Seiten N bis M (für Large-PDFs gezielt)
- `-enc UTF-8` (default): Unicode

### Step 3: Read mit Claude

```
Read file_path="/tmp/extracted.txt"
```

Claude liest die Text-File mit normalen Read-Tokens (sehr billig — ~250 Tokens/1k Zeichen).

### Step 3b: Multi-Modal-PDF Pattern (Text-Tabellen + 1 kritisches Chart)

Häufiger Fall: Datenblatt mit Text-Tabellen (T/S-Parameter, Mounting-Dimensions) **plus** einem kritischen Chart (Frequency-Response, SPL-Kurve). Hybrid-Approach:

```bash
# 1. Text via pdftotext (alle Text-Tabellen)
pdftotext -layout "/path/to/doc.pdf" /tmp/extracted.txt

# 2. Chart-Seite identifizieren — pdfinfo zeigt Seitenzahl, Read der Text-Extraktion
#    zeigt welche Seite "Figure X" oder "Frequency Response" referenziert
# 3. NUR die Chart-Seite via Vision-Read laden (Read mit pages="N-N")
```

Spart 80-90% Tokens vs. komplettes Vision-Reading, behält aber Chart-Visual-Information wo sie wichtig ist.

### Step 4: OCR-Fallback bei Scan-PDFs

Wenn Step 1 leer ergab:

```bash
# Optionaler OCR-Schritt (poppler hat keinen, brauchen ocrmypdf)
brew install ocrmypdf tesseract
ocrmypdf "/path/to/scan.pdf" /tmp/with-ocr.pdf  # adds text layer
pdftotext /tmp/with-ocr.pdf /tmp/extracted.txt
```

`ocrmypdf` ist deutlich schneller (~30s pro 20-Seiten-PDF mit deutscher Sprache) als Claude Vision für 20 Seiten (~20s pro Seite × 20 = 400s) und produziert wieder-verwendbare Text-Layer im PDF.

## Anti-Patterns

- ❌ **PDF direkt mit Read-Tool laden** ohne pdftotext-Vorab-Probe — verschwendet Tokens auf Vision-Side
- ❌ **`pdftotext -layout` per Default** — bei normalem Fließtext erzeugt das unnötige Whitespace-Spalten. Nur bei Tabellen/Multi-Column nutzen
- ❌ **OCR auf bereits text-text-layered PDFs** — `ocrmypdf` ist langsam; erst `pdftotext`-Probe machen
- ❌ **Auto-Skill-Anwendung auf jedes PDF** — Layout-/Bild-zentrische PDFs (CAD-Drawings, Mockups) profitieren von Vision

## Cost-of-Skipping

| Skill-Anwendung | Tokens für 20-Seiten-PDF | Cost (Fable-Pricing) |
|---|---|---|
| ❌ Skip (Claude Vision direkt) | 40-100k Input-Tokens | $0.40 - $1.00 |
| ✅ Apply (pdftotext + Read) | ~8-15k Read-Tokens | $0.08 - $0.15 |
| **Saving** | **80-85%** | **~$0.30-0.85 pro PDF** |

Bei 10 PDFs/Monat Saving = $3-8/Monat allein durch dieses Skill. Bei Opus-im-Plan: bewahrt Plan-Limit vor sinnloser Verbrennung.

## Cross-Skill-Connections

- `obsidian-vault-folder-restructure`: relevant wenn extrahierte Text-Files in `07 Anhänge/` archiviert werden statt nur Temp
- `briefing-source-triangulation`: bei mehreren PDF-Quellen für ein Thema (Notar + Käufer-Anwalt + Versicherung) — alle erst extrahieren, dann triangulieren
- `code-review-backlog-cost-warning`: gleiche Domäne (Token-Cost-Bewusstsein als Disziplin)
- `docx-tab-position-extraction-for-layout-replication`: Schwester-Skill für DOCX-Files (XML-Extraktion statt Vision)

## Quell-Triggers

- Wolf-Brain-Dump 05.06.2026: „Token-Optimierung — eigene Tools (zum Beispiel pdf per Python anstatt Claude in Txt umwandeln)"
- Wolf-Session 11.06.2026: Tool-4-Auftrag „PDF-Extract Skill" als Teil der 4 Token-Optimierungs-Tools
- Existing Vault-Pattern: `07 Anhänge/pdf_dayton audio_PS95-8_1.pdf` und ähnliche PDFs werden regelmäßig als Quellen referenziert

---

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill, Scenario: 20-Seiten Dayton-Audio-Datenblatt, 3 Sektionen extrahieren): Default-Reflex `Read(file_path=..., pages="1-10")` + `pages="11-20")` — würde 10-25k Vision-Tokens kosten. Self-Assessment am Ende: „Mein Default-Approach ist suboptimal — ich starte mit dem teuersten Tool (Read mit Vision-Möglichkeit) ohne vorher zu prüfen ob pdftotext reicht." RED-Subagent identifizierte pdftotext als „disziplinierten Approach" **nur nachträglich** in der Reflexion, nicht als spontanen Default. Klassisches Anti-Pattern: schon Trainings-bekannt aber nicht ohne Skill-Trigger angewendet.

- **GREEN-Subagent** (mit Skill via Read-Tool): Las erst `Overview` (Token-Cost-Begründung), dann `When to Trigger` (Match-Check), dann `Steps`. Hielt explizit Anti-Patterns-Block gegen eigenen Plan (`-layout` bewusst gewählt für Tabellen-Datenblatt, NICHT als Default). Token-Cost-Schätzung 1-3k statt 40-100k — **~90% Saving empirisch bestätigt**. Caller-Context-Check: `pdftotext v26.04.0` lokal verfügbar (`/opt/homebrew/bin/pdftotext`).

- **Refactor angewendet vor PROMOTE**:
  - **Polish-1**: Step 0 `pdfinfo`-Metadaten-Probe hinzugefügt — verifiziert User-Behauptungen wie „20 Seiten" bevor Approach gewählt wird (RED-Subagent erkannte zu Recht dass User-Behauptungen oft falsch sind)
  - **Polish-2**: Step 3b „Multi-Modal-PDF Pattern" hinzugefügt — Hybrid (Text via pdftotext + nur Chart-Seite via Vision) als explizit dokumentierter Pattern, war vorher nur in Alt-3 versteckt

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Cleanup-Hinweis für /tmp/-Files** — bei Vault-CWD relative Pfade vermeiden, immer absolute `/tmp/` nutzen (GREEN-Subagent-Selbstdisziplin, sollte explizit dokumentiert sein)
2. **Privacy-Boundary-Note** — bei `vertraulich`-Tag-PDFs (Notar, Verträge, Renten-Eckdaten) Temp-File in `/tmp/` umgeht Hook-Detection (CLAUDE.md 24.05.). Edge-Case aber relevant für Wolfs Privacy-Disziplin
3. **Token-Cost-Tracking-Praxis** — wie misst man real die Token-Differenz? `~/Library/Logs/anthropic-billing/` ist heuristisch; bessere Metrik wäre wünschenswert
4. **Cross-Skill mit `obsidian-vault-folder-restructure`** — wenn extrahierte Text-Files dauerhaft im Vault landen sollen, gehören sie in `04 Ressourcen/` nicht `/tmp/`

---

_Erstellt 2026-06-11 ~15:00 UTC nach Health-Aggregator-Spec während Token-Optimierungs-Session 4-Tool-Block.  
Promoted 2026-06-12 nach TDD-Cycle 1 PASS via `skill-tdd-promotion-workflow` (RED+GREEN-Subagent-Pair, 2 Polish-Items pre-PROMOTE eingebaut)._
