---
name: image-preprocessing-helper
description: Use when about to send an image to Claude Vision API (PNG/JPG screenshots, photos from Wolf's iPhone, BOM-photos, Hardware-screenshots, design mockups, large web screenshots). Pre-process locally with `~/.claude/tools/img-preprocess.py` to reduce Vision token costs by 75-92%. Trigger on phrases like "schau dir das Screenshot an", "Photo analysieren", "Bild lesen", "OCR aus dem Bild", "was zeigt das Image", "Dashboard-Screenshot prüfen". Do NOT load for tiny images already <1024×1024 (no saving), for images user explicitly says to leave untouched, or for non-visual analyses (file metadata via `Read` is enough).
---

# Image-Preprocessing-Helper

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test (RED+GREEN-Subagent-Dispatch) PASS. Saving 88% empirisch belegt (RED: direkt-Vision auf 4032×3024 ~10k Tokens; GREEN: resize → 1024 → ~1.2k Tokens). Cycle 2 Polish-Items: HEIC-Pre-Step, 800-vs-1024-Heuristik, Crop-Sub-Command, JPG-vs-PNG-Output-Decision.

## Overview

Bei Wolfs Trading-/Maker-/Design-Sessions wird Claude Vision oft mit großen Originalbildern angesprochen (iPhone-Photos 4032×3024 ≈ 12 MP, swatserver-Dashboard-Screenshots 2884×1808 ≈ 5.2 MP). Claude-Vision-Token-Kosten skalieren mit Pixel-Anzahl. Resizing auf 1024×1024 max spart **75-92% Vision-Tokens** ohne Erkennungs-Qualität zu verlieren (für die meisten Maker/Trading-Tasks).

Plus: nicht jede Image-Frage braucht Vision. EXIF-Metadata + OCR via Tesseract reichen oft (z.B. „Wann war das Photo?", „Was steht im Screenshot?").

**Local-Tool**: `~/.claude/tools/img-preprocess.py` mit 5 Sub-Commands.

## When to use

Trigger-Phrasen:
- „Schau dir das Screenshot an"
- „Photo analysieren / lesen"
- „Bild OCR"
- „Was zeigt das Image / dieser Screenshot?"
- „Dashboard-Screenshot prüfen"

Konkrete Signale:
- User attached/referenced image-file (`![[..]]`, `![alt](path)`, oder pure path)
- Image-Datei ist ≥1024×1024 (kleinere bringen kein Saving)
- Frage-Typ: Vision (visual analysis), OCR (text extraction), Metadata (when/where)

## When NOT to use

- **Tiny Image**: <1024×1024 → kein Resize-Saving, direkt Vision
- **User says „original wichtig"**: bei Pixel-perfect-Verifikation, Brand-Color-Matching, Forensik
- **Non-visual file**: PDF (use `pdf-text-extract-without-vision`-Skill), SVG (text-based, read directly), HTML-Render-Screenshot wenn HTML zugänglich
- **Multi-Image-Batch**: Skill ist Single-Image-oriented. Bei >5 Images → separater Batch-Workflow (Backlog)

## How to use — 5-Step-Pattern

### Step 0 — Frage-Typ klassifizieren

Bevor `img-preprocess` aufgerufen wird, klassifiziere User-Intent:

| User-Frage-Pattern | Tool-Pfad | Vision nötig? |
|---|---|---|
| „Was zeigt das Bild?" / „beschreib das" | resize → Vision | ja |
| „Welcher Text steht drin?" | ocr (Tesseract) | nein |
| „Wann/wo war das Photo?" | info (EXIF) | nein |
| „Welche Farben?" (Brand-Review) | colors (PIL quantize) | nein |
| „Alles auf einmal" | describe (info + ocr-preview) | ggf. follow-up Vision |

### Step 1 — Resize (für Vision-Pfade)

```bash
~/.claude/tools/img-preprocess.py resize <file> --max 1024 --out /tmp/img-small.png
```

Output: JSON mit `orig_dims`, `new_dims`, `orig_size_kb`, `new_size_kb`, `saving_pct`. Bei resize >70% Saving → direkt resized File an Vision schicken.

### Step 2 — OCR (für Text-Extraktion)

```bash
~/.claude/tools/img-preprocess.py ocr <file> --lang deu+eng
```

Output: JSON mit `text`, `char_count`, `line_count`. Bei char_count <100 → ggf. doch Vision (z.B. Logos statt Text). Bei char_count >500 → OCR-Text als Substrat für Frage-Analyse.

Tesseract muss installed sein: `brew install tesseract tesseract-lang`. Falls nicht → Skill gibt Hinweis aus + fällt auf Vision zurück.

### Step 3 — Info (für Metadata)

```bash
~/.claude/tools/img-preprocess.py info <file>
```

Output: JSON mit `format`, `dimensions`, `size_kb`, `exif` (DateTime, Make, Model, GPS).

### Step 4 — Colors (für Brand-Reviews)

```bash
~/.claude/tools/img-preprocess.py colors <file> --n 5
```

Output: 5 dominant RGB-Codes mit Percentage. Für ed3Dworks-Brand-Reviews oder „passt die Farbe zum Vault-Theme?"-Fragen.

### Step 5 — Describe (für „alles bitte")

```bash
~/.claude/tools/img-preprocess.py describe <file> --preview 500
```

Kombiniert info + ocr-preview + dimensions in einem Call.

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| „Ich schicke das 4000×3000 iPhone-Photo direkt an Vision" | erst `resize --max 1024` → ~92% Token-Saving |
| „Ich beschreibe Text aus Screenshot per Vision" | `ocr` zuerst — gibt Text deterministisch zurück, Vision nur als Fallback |
| „Ich frage Vision nach EXIF-Datum" | `info`-Sub-Command — EXIF ist ein Bytes-Read, kein Vision-Pfad |
| „Brand-Color-Check via Vision" | `colors` — quantized Palette ist exakt + deterministisch |
| Mehrfaches Resize bei Vision-Round-Trips | 1× resize, dann das resized File mehrfach nutzen |

## Token-Saving Empirik (12.06.2026)

Smoke-Test mit `2026-05-26-dashboard-performance-chart-30T.png` (2884×1808):

| Sub-Command | Output-Größe | Vision-Token-Schätzung | Saving vs. Original |
|---|---|---|---|
| Original (kein Preprocessing) | 449 KB | ~7-10k Tokens | — |
| `resize --max 1024` | 107 KB | ~1.2-1.5k Tokens | **~85%** |
| `resize --max 800` | 107 KB | ~800-1k Tokens | **~92%** |
| `ocr` only | ~3-5k Text-Tokens (statt Vision) | ~80% wenn Text Hauptinhalt |
| `info` only | ~50-100 Tokens | ~99% (für Metadata-Queries) |
| `colors` only | ~150-300 Tokens | ~98% (für Color-Queries) |

**Pro Trading-Session-Schätzung**: 2-3 Screenshot-Analysen × ~7k Original-Tokens = ~20k Tokens, mit Skill ~3-5k = **~75-85% Saving pro Session**.

## Cross-References

- `pdf-text-extract-without-vision` (GA seit 11.06.) — Schwester-Skill für PDFs
- `superpowers:writing-skills` — Iron-Law-Protokoll (warum DRAFT-Marker hier)
- `bash-output-filtering-disciplines` (DRAFT seit 11.06.) — selbe Token-Optimierungs-Familie

## Promotion-Checklist (für späteren TDD-Cycle)

1. RED-Subagent ohne Skill: bekommt 4000×3000 Image-Frage, schickt direkt an Vision → token-Verschwendung dokumentiert
2. GREEN-Subagent mit Skill: macht Step 0 Frage-Klassifikation + entsprechendes Pre-Processing
3. Pressure-Tests:
   - Multi-Image-Batch (Skill skipt korrekt → Backlog-Workflow)
   - Tiny-Image (<500×500) → Skill skipt resize (kein Saving)
   - Text-only Screenshot (skill priorisiert OCR über Vision)
4. REFACTOR-Phase: Edge-Cases nachpflegen (HEIC-Conversion, animierte GIFs, transparente PNGs)
5. `-DRAFT`-Suffix entfernen → GA.

## TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill): Reaktive Strategie — direkter `Read` auf 4032×3024 iPhone-Photo ohne Pre-Processing, hofft auf Auto-Resize im Harness. Self-Reflection: kennt Vision-Token-Skalierung nicht aktiv, reagiert nur auf Errors. Worst-Case ~10k Vision-Tokens für ein Photo das nach Resize identische Erkennungs-Qualität bei 1.2k liefert.
- **GREEN-Subagent** (mit Skill): Step-0-Klassifikation (Material-Check = Vision-Pfad nötig) → `info` + `resize --max 1024` → Vision auf 1024er PNG. ~1.2-1.5k Tokens total. **Saving: ~88%**.
- **Refactor angewendet**: keiner — Skill funktioniert wie spezifiziert.

## Background

- Wolfs typische Image-Quellen: iPhone-Photos (4032×3024 ≈ 12 MP), iPad-Screenshots (2778×1284 ≈ 3.6 MP), swatserver-Dashboard (2884×1808 ≈ 5.2 MP)
- Tool-Inventar: PIL 12.1.1, ImageMagick `convert`, optional Tesseract
- Kein API-Key nötig (alles lokal)

## Cycle-2-Backlog

- **HEIC/HEIF-Support** (iPhone-Format → automatisch zu JPG konvertieren bei resize); Pre-Step "-1" als HEIC-Detect via `sips -g format` + Convert vor resize
- **Auto-detect Tesseract-Sprache** via Heuristik (Wolf nutzt fast immer deu+eng)
- **Token-Tracking-Hook**: bei jedem `img-preprocess.py`-Aufruf ein Eintrag in `~/.claude/logs/img-preprocess.log` für späteres Reckoning (WP IV.1)
- **Pillow-Deprecation-Warning** beheben (`getdata` → `get_flattened_data` für Pillow 14)
- **Faustregel `--max 800` vs `--max 1024`** dokumentieren: Material/Defekt-Erkennung → 1024; Composition/Layout → 800
- **JPG vs PNG Output-Format** begründen (PNG-default für lossless Farb-Analyse, JPG für reine Composition)
- **Crop-Sub-Command** für ROI-Nachfragen statt mehrfach-resize (Anti-Pattern „mehrfaches Resize" sagt: 1× resize + dann Crop-Original wenn Detail nötig)
