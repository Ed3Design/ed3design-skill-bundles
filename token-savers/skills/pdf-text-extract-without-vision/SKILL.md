---
name: pdf-text-extract-without-vision
description: Use BEFORE reading any PDF file when the goal is to extract textual content (specs, contracts, articles, manuals, financial reports, legal documents). STOP and run `pdftotext` from the poppler-utils package locally instead of letting Claude read the PDF directly. Claude Vision burns 1-5k tokens per page even for text-heavy PDFs that are 100% mechanically extractable. `pdftotext` is a free local CLI tool (already installed at /opt/homebrew/bin/pdftotext, version 26.04.0+ for poppler v26+) that converts the PDF text-layer to plain UTF-8 markdown-ish text at zero token cost. Trigger on phrases like "read this PDF", "extract text from PDF", "what's in the PDF", "summarize the PDF", "analyze PDF", "show PDF content", "get text from the document", "read spec from PDF", "evaluate contract from PDF", "evaluate manual", any user request involving "PDF" + content comprehension. Do NOT use for image-only PDFs (scans without OCR'd text layer — pdftotext returns empty; fall back to Claude Vision OR run `ocrmypdf` first), for PDFs where the LAYOUT is the primary information (architectural drawings, design mockups, infographics — there the visual structure matters), for PDFs less than ~1 page where token cost is negligible (~500 tokens total), or for PDFs that contain critical embedded images Claude must SEE not READ (charts where the trend shape matters more than the data table). Encodes a token-optimization finding: Claude Vision for typical text-heavy PDFs (specs, manuals, financial reports) is 5-20x more expensive than pdftotext + Read tool.

---

# PDF-Text-Extract without Vision

> ✅ **PROMOTED** via TDD-Cycle (RED+GREEN subagent pair). RED subagent self-reflected "my default approach (direct Read with pages param) is suboptimal" — skill prevents exactly this default-Vision trap. GREEN subagent achieved ~90% token reduction with `-layout` deliberately chosen for a tabular datasheet.

## Overview

Brain-dump item: *"critical analysis of token usage — own tools (for example pdf or img via Python instead of Claude converting to text)"*

Claude Vision processes every PDF page as an image → **1-5k tokens per page** even for pure text PDFs. For a 20-page spec = 20-100k tokens **just for reading**, before any analysis. Completely avoidable when the PDF has a text layer (true for ~95% of all modern PDFs).

`pdftotext` from `poppler-utils` (installed locally on macOS via Homebrew) extracts the text layer at **0 tokens** server-cost and returns plain text, which Claude reads efficiently via the `Read` tool.

## When to Trigger

✅ **YES — pdftotext-first:**
- User says "read this PDF" / "summarize PDF" / "spec from PDF"
- PDF in vault under attachments or referenced as an external path
- PDF comes from official sources (court records, notary, government, manuals, whitepapers, ML papers)
- > 2 pages **or** text-focused content

❌ **NO — keep Vision:**
- PDF is a scanned original (no text layer) → run `ocrmypdf` first, then pdftotext
- Layout/visuals are the information (architecture plans, mockups, charts where the trend shape matters more than the numbers)
- Very small PDFs (1 page, ~500 tokens) where setup overhead is not worth it
- PDF contains critical embedded diagrams Claude should SEE, not read

## Steps

### Step 0: Metadata probe (verify page count + size)

User claims about PDFs ("20-page spec", "only 1 page") are often wrong. Verify before choosing an approach:

```bash
pdfinfo "/path/to/doc.pdf" | grep -E "Pages|File size|Page size"
# Pages:           1
# File size:       244532 bytes
# Page size:       612 x 792 pts (letter)
```

If `Pages: 1` → token cost for direct Vision is also low (~2-5k); skill setup overhead may not be worth it. If `Pages: >5` → skill clearly worth it. If `Pages: 20+` → MUST-USE.

### Step 1: Path check + text-layer probe

```bash
# Check tool available
which pdftotext || brew install poppler

# Quick probe: does the PDF have a text layer?
pdftotext -nopgbrk "/path/to/doc.pdf" - | head -20
```

If output is empty / only whitespace → PDF is scan-based, fall back to OCR (see Step 4) or Vision.

### Step 2: Full extraction to temp file

```bash
# Standard variant: a flat text file
pdftotext -nopgbrk "/path/to/doc.pdf" /tmp/extracted.txt

# Layout-aware variant (for tables / multi-column text):
pdftotext -layout "/path/to/doc.pdf" /tmp/extracted-layout.txt

# With page numbers as header (helpful for long specs):
pdftotext "/path/to/doc.pdf" -  # default: form-feed \f as page separator
```

**Flag tips:**
- `-nopgbrk`: no `\f` page separator (flat text)
- `-layout`: preserves table structure (columns via whitespace)
- `-raw`: keep original text-order (sometimes better for complex layouts)
- `-f N -l M`: only pages N to M (targeted for large PDFs)
- `-enc UTF-8` (default): Unicode

### Step 3: Read with Claude

```
Read file_path="/tmp/extracted.txt"
```

Claude reads the text file with normal Read tokens (very cheap — ~250 tokens/1k characters).

### Step 3b: Multi-Modal-PDF pattern (text tables + 1 critical chart)

Common case: datasheet with text tables (T/S parameters, mounting dimensions) **plus** one critical chart (frequency response, SPL curve). Hybrid approach:

```bash
# 1. Text via pdftotext (all text tables)
pdftotext -layout "/path/to/doc.pdf" /tmp/extracted.txt

# 2. Identify chart page — pdfinfo shows page count, Read of the text extraction
#    shows which page references "Figure X" or "Frequency Response"
# 3. Load ONLY the chart page via Vision-Read (Read with pages="N-N")
```

Saves 80-90% tokens vs. complete Vision reading, but keeps chart visual information where it matters.

### Step 4: OCR fallback for scan PDFs

If Step 1 came up empty:

```bash
# Optional OCR step (poppler has none, need ocrmypdf)
brew install ocrmypdf tesseract
ocrmypdf "/path/to/scan.pdf" /tmp/with-ocr.pdf  # adds text layer
pdftotext /tmp/with-ocr.pdf /tmp/extracted.txt
```

`ocrmypdf` is significantly faster (~30s per 20-page PDF with German language) than Claude Vision for 20 pages (~20s per page × 20 = 400s) and produces a reusable text layer in the PDF.

## Anti-Patterns

- ❌ **Loading PDF directly with Read tool** without pdftotext preliminary probe — wastes tokens on the Vision side
- ❌ **`pdftotext -layout` by default** — produces unnecessary whitespace columns for normal flowing text. Only use for tables/multi-column
- ❌ **OCR on already text-layered PDFs** — `ocrmypdf` is slow; do `pdftotext` probe first
- ❌ **Auto-applying skill to every PDF** — layout/image-centric PDFs (CAD drawings, mockups) benefit from Vision

## Cost-of-Skipping

| Skill application | Tokens for 20-page PDF | Cost (sample pricing) |
|---|---|---|
| ❌ Skip (direct Claude Vision) | 40-100k input tokens | $0.40 - $1.00 |
| ✅ Apply (pdftotext + Read) | ~8-15k Read tokens | $0.08 - $0.15 |
| **Saving** | **80-85%** | **~$0.30-0.85 per PDF** |

At 10 PDFs/month, savings = $3-8/month from this skill alone.

## Cross-Skill-Connections

- `obsidian-vault-folder-restructure`: relevant when extracted text files are archived in attachments instead of just temp
- `briefing-source-triangulation`: with multiple PDF sources on a topic (notary + buyer's lawyer + insurance) — extract all first, then triangulate
- `code-review-backlog-cost-warning`: same domain (token-cost awareness as discipline)
- `docx-tab-position-extraction-for-layout-replication`: sister skill for DOCX files (XML extraction instead of Vision)

## Source Triggers

- Brain-dump: "token optimization — own tools (for example pdf via Python instead of Claude converting to text)"
- Token-optimization session: tool item "PDF-Extract skill" as part of a 4-tool block
- Existing vault pattern: PDFs are regularly referenced as sources

---

## Background: TDD Trail (Bulletproofing Log)

### Cycle 1 — PASS

- **RED subagent** (without skill, scenario: 20-page audio-driver datasheet, extract 3 sections): default reflex `Read(file_path=..., pages="1-10")` + `pages="11-20")` — would cost 10-25k Vision tokens. Self-assessment at the end: "My default approach is suboptimal — I start with the most expensive tool (Read with Vision possibility) without first checking whether pdftotext is enough." RED subagent identified pdftotext as "the disciplined approach" **only afterwards** in reflection, not as a spontaneous default. Classic anti-pattern: known from training but not applied without a skill trigger.

- **GREEN subagent** (with skill via Read tool): read `Overview` first (token-cost reasoning), then `When to Trigger` (match check), then `Steps`. Explicitly held the anti-patterns block against its own plan (`-layout` deliberately chosen for tabular datasheet, NOT as default). Token-cost estimate 1-3k instead of 40-100k — **~90% saving empirically confirmed**. Caller-context check: `pdftotext v26.04.0` available locally (`/opt/homebrew/bin/pdftotext`).

- **Refactor applied before PROMOTE**:
  - **Polish-1**: Added Step 0 `pdfinfo` metadata probe — verifies user claims like "20 pages" before approach selection (RED subagent rightly recognized that user claims are often wrong)
  - **Polish-2**: Added Step 3b "Multi-Modal-PDF pattern" — hybrid (text via pdftotext + only chart page via Vision) as explicitly documented pattern, was previously hidden in Alt-3

### Cycle-2 Backlog (Polish, non-blocking)

1. **Cleanup hint for /tmp/ files** — avoid vault-CWD relative paths, always use absolute `/tmp/` (GREEN subagent self-discipline, should be explicitly documented)
2. **Privacy boundary note** — for confidential-tagged PDFs (notary, contracts, retirement data) a temp file in `/tmp/` bypasses hook detection. Edge case but relevant for privacy discipline
3. **Token-cost-tracking practice** — how to actually measure the token difference? `~/Library/Logs/anthropic-billing/` is heuristic; a better metric would be desirable
4. **Cross-skill with `obsidian-vault-folder-restructure`** — when extracted text files should permanently land in the vault, they belong in resources, not `/tmp/`
