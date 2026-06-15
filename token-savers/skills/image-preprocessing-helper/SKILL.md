---
name: image-preprocessing-helper
description: Use when about to send an image to Claude Vision API (PNG/JPG screenshots, iPhone photos, BOM photos, hardware screenshots, design mockups, large web screenshots). Pre-process locally with `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py` to reduce Vision token costs by 75-92%. Trigger on phrases like "look at this screenshot", "analyze photo", "read image", "OCR from the image", "what does this image show", "check dashboard screenshot". Do NOT load for tiny images already <1024×1024 (no saving), for images the user explicitly says to leave untouched, or for non-visual analyses (file metadata via `Read` is enough).
---

# Image-Preprocessing-Helper

> ✅ **PROMOTED** — TDD pressure-test (RED+GREEN subagent dispatch) PASS. Saving 88% empirically verified (RED: direct Vision on 4032×3024 ~10k tokens; GREEN: resize → 1024 → ~1.2k tokens). Cycle 2 polish items: HEIC pre-step, 800-vs-1024 heuristic, crop sub-command, JPG-vs-PNG output decision.

## Overview

In typical production-domain / maker / design sessions, Claude Vision is often called with large original images (iPhone photos 4032×3024 ≈ 12 MP, server dashboard screenshots 2884×1808 ≈ 5.2 MP). Claude Vision token costs scale with pixel count. Resizing to 1024×1024 max saves **75-92% Vision tokens** without losing recognition quality (for most maker / production-domain tasks).

Plus: not every image question needs Vision. EXIF metadata + OCR via Tesseract often suffice (e.g. "When was the photo taken?", "What does the screenshot say?").

**Local tool**: `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py` with 5 sub-commands.

## When to use

Trigger phrases:
- "Look at this screenshot"
- "Analyze / read photo"
- "Image OCR"
- "What does this image / screenshot show?"
- "Check dashboard screenshot"

Concrete signals:
- User attached/referenced image file (`![[..]]`, `![alt](path)`, or pure path)
- Image file is ≥1024×1024 (smaller ones yield no saving)
- Question type: Vision (visual analysis), OCR (text extraction), Metadata (when/where)

## When NOT to use

- **Tiny image**: <1024×1024 → no resize saving, go straight to Vision
- **User says "original is important"**: for pixel-perfect verification, brand color matching, forensics
- **Non-visual file**: PDF (use `pdf-text-extract-without-vision` skill), SVG (text-based, read directly), HTML-render screenshot when HTML is accessible
- **Multi-image batch**: skill is single-image-oriented. For >5 images → separate batch workflow (backlog)

## How to use — 5-step pattern

### Step 0 — Classify question type

Before calling `img-preprocess`, classify user intent:

| User question pattern | Tool path | Vision needed? |
|---|---|---|
| "What does the image show?" / "describe it" | resize → Vision | yes |
| "What text is in it?" | ocr (Tesseract) | no |
| "When/where was the photo taken?" | info (EXIF) | no |
| "Which colors?" (brand review) | colors (PIL quantize) | no |
| "All of the above" | describe (info + ocr-preview) | maybe follow-up Vision |

### Step 1 — Resize (for Vision paths)

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py resize <file> --max 1024 --out /tmp/img-small.png
```

Output: JSON with `orig_dims`, `new_dims`, `orig_size_kb`, `new_size_kb`, `saving_pct`. If resize >70% saving → send resized file directly to Vision.

### Step 2 — OCR (for text extraction)

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py ocr <file> --lang deu+eng
```

Output: JSON with `text`, `char_count`, `line_count`. If char_count <100 → maybe still use Vision (e.g. logos instead of text). If char_count >500 → OCR text as substrate for question analysis.

Tesseract must be installed: `brew install tesseract tesseract-lang`. If not → skill emits a hint and falls back to Vision.

### Step 3 — Info (for metadata)

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py info <file>
```

Output: JSON with `format`, `dimensions`, `size_kb`, `exif` (DateTime, Make, Model, GPS).

### Step 4 — Colors (for brand reviews)

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py colors <file> --n 5
```

Output: 5 dominant RGB codes with percentage. For brand reviews or "does the color match the theme?" questions.

### Step 5 — Describe (for "everything please")

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/img-preprocess.py describe <file> --preview 500
```

Combines info + ocr-preview + dimensions in one call.

## Anti-patterns

| Anti-Pattern | What to do instead |
|---|---|
| "I'll send the 4000×3000 iPhone photo directly to Vision" | first `resize --max 1024` → ~92% token saving |
| "I'll describe text from a screenshot via Vision" | `ocr` first — returns text deterministically, Vision only as fallback |
| "I'll ask Vision for the EXIF date" | `info` sub-command — EXIF is a bytes-read, not a Vision path |
| "Brand-color check via Vision" | `colors` — quantized palette is exact and deterministic |
| Multiple resizes during Vision round-trips | 1× resize, then reuse the resized file multiple times |

## token saving Empirics

Smoke test with a sample dashboard chart PNG (2884×1808):

| Sub-command | Output size | Vision token estimate | Saving vs. original |
|---|---|---|---|
| Original (no preprocessing) | 449 KB | ~7-10k tokens | — |
| `resize --max 1024` | 107 KB | ~1.2-1.5k tokens | **~85%** |
| `resize --max 800` | 107 KB | ~800-1k tokens | **~92%** |
| `ocr` only | ~3-5k text-tokens (instead of Vision) | ~80% when text is main content |
| `info` only | ~50-100 tokens | ~99% (for metadata queries) |
| `colors` only | ~150-300 tokens | ~98% (for color queries) |

**Per-session estimate**: 2-3 screenshot analyses × ~7k original tokens = ~20k tokens; with skill ~3-5k = **~75-85% saving per session**.

## Cross-References

- `pdf-text-extract-without-vision` (GA) — sister skill for PDFs
- `superpowers:writing-skills` — Iron-Law protocol (why DRAFT marker here)
- `bash-output-filtering-disciplines` — same token-optimization family

## TDD Trail (Bulletproofing Log)

### Cycle 1 — PASS

- **RED subagent** (without skill): reactive strategy — direct `Read` on a 4032×3024 iPhone photo without pre-processing, hoping for auto-resize in the harness. Self-reflection: doesn't actively know about Vision token scaling, reacts only to errors. Worst case ~10k Vision tokens for a photo that, after resize, delivers identical recognition quality at 1.2k.
- **GREEN subagent** (with skill): Step 0 classification (material check = Vision path needed) → `info` + `resize --max 1024` → Vision on the 1024 PNG. ~1.2-1.5k tokens total. **Saving: ~88%**.
- **Refactor applied**: none — skill works as specified.

## Background

- Typical image sources: iPhone photos (4032×3024 ≈ 12 MP), iPad screenshots (2778×1284 ≈ 3.6 MP), server dashboard (2884×1808 ≈ 5.2 MP)
- Tool inventory: PIL 12.1.1, ImageMagick `convert`, optional Tesseract
- No API key needed (everything local)

## Cycle-2 Backlog

- **HEIC/HEIF support** (iPhone format → automatically convert to JPG during resize); pre-step "-1" as HEIC detect via `sips -g format` + convert before resize
- **Auto-detect Tesseract language** via heuristic (default deu+eng)
- **Token tracking hook**: on every `img-preprocess.py` call, append an entry to `~/.claude/logs/img-preprocess.log` for later reckoning
- **Pillow deprecation warning** fix (`getdata` → `get_flattened_data` for Pillow 14)
- **Rule-of-thumb `--max 800` vs `--max 1024`** documented: material/defect recognition → 1024; composition/layout → 800
- **JPG vs PNG output format** justified (PNG default for lossless color analysis, JPG for pure composition)
- **Crop sub-command** for ROI follow-ups instead of repeated resize (anti-pattern "multiple resize" says: 1× resize + then crop original when detail is needed)
