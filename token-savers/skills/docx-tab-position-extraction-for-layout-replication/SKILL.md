---
name: docx-tab-position-extraction-for-layout-replication
description: |-
  Use when replicating a document layout (business letter, invoice, contract) from an existing Word `.docx` file in HTML/CSS/PDF/Print-CSS — a user provides a previous Word document as "make my web letter look like THIS" and you need precise tab-stop / margin / indentation positions. STOP and extract the actual measurements from the DOCX XML before writing CSS by eye. DOCX is a ZIP-archive containing `word/document.xml`; tab stops live in `<w:tab w:pos="6803" />` where `w:pos` is in **twips** (1/1440 inch); convert with `mm = twips ÷ 1440 × 25.4`. The same applies to margins (`<w:pgMar>`), indentation (`<w:ind>`), and column widths (`<w:gridCol>`). Trigger on phrases like "replicate the layout from my old Word letter", "make the layout like the DOCX", "convert twips to mm", "measure the layout, don't estimate it". Do NOT load for designing a layout from scratch, for `.doc` binary legacy format (convert via LibreOffice headless first), for `.docx` where layout is irrelevant, or when the reference is a PDF.
---

# DOCX Tab-Position Extraction for Layout Replication

> ⚠️ **DRAFT** — needs TDD-Promotion (RED: replicate a reference DOCX letter by visual estimation → measure deviation; GREEN: extract from XML → verify deviation drops). See `skill-tdd-promotion-workflow`.

## Overview

When a reference letter (or any reference DOCX) needs to look "exactly" like the original, the measurements are **already stored inside the DOCX** — you only have to extract them instead of estimating.

DOCX = ZIP container. Most important file: `word/document.xml`. All layout measurements are encoded there as XML attributes, almost always in **twips** (1 twip = 1/1440 inch = ~0.0176 mm).

**Conversion** (central formula):
```
mm  =  twips ÷ 1440 × 25.4
inch =  twips ÷ 1440
pt   =  twips ÷ 20      (1 pt = 20 twips, for font sizes)
```

## When to use

Trigger phrases:
- "make the layout exactly like my old letter"
- "DIN 5008 but adapted to my template"
- "take the tab stops from the DOCX"
- "replicate the letter template"
- "why is the date wrong — check the DOCX"

## When NOT to use

- Layout design from scratch without a reference DOCX
- `.doc` (binary, pre-2007) — first convert to `.docx` via LibreOffice headless: `soffice --headless --convert-to docx file.doc`
- PDF as reference — different tools (`pdfinfo`, manual ruler measurement in Acrobat)
- DOCX content extraction (names, date fields, recipient addresses) — not a layout skill, use the `python-docx` library for structured reads

## The 4-Step Extraction

### Step 1 — Unzip

```bash
unzip -o reference.docx -d /tmp/ref-extracted
ls /tmp/ref-extracted/word/
# document.xml, styles.xml, settings.xml, header*.xml, footer*.xml ...
```

### Step 2 — Find the relevant elements

```bash
# Tab stops
grep -oE '<w:tab[^/]+/>' /tmp/ref-extracted/word/document.xml | head -20
# Example output: <w:tab w:val="right" w:pos="6803"/>

# Page margins
grep -oE '<w:pgMar[^/]+/>' /tmp/ref-extracted/word/document.xml
# Example: <w:pgMar w:top="1417" w:right="1417" w:bottom="1134" w:left="1417" w:header="708" w:footer="708"/>

# First-line indent
grep -oE '<w:ind[^/]+/>' /tmp/ref-extracted/word/document.xml | head -5
```

### Step 3 — Convert twips → mm

| Element attribute | Example twips | mm | Meaning |
|---|---|---|---|
| `<w:tab w:pos="6803">` | 6803 | **120.0 mm** | right-aligned tab stop at 120mm |
| `<w:pgMar w:left="1417">` | 1417 | **25.0 mm** | left page margin |
| `<w:pgMar w:top="1417">` | 1417 | **25.0 mm** | top page margin |
| `<w:ind w:firstLine="709">` | 709 | **12.5 mm** | first-line indent |

Quick converter:
```python
def twips_to_mm(twips: int) -> float:
    return round(twips / 1440 * 25.4, 1)

# 6803 -> 120.0
# 1417 -> 25.0
# 708  -> 12.5
```

### Step 4 — Apply in target medium

**HTML/CSS for print letter** (DIN 5008):
```css
@page {
  size: A4;
  margin: 25mm 25mm 20mm 25mm;  /* from pgMar */
}
.letter-greeting-line {
  display: grid;
  grid-template-columns: auto 1fr;
}
.letter-greeting-line .date {
  margin-left: 120mm;   /* from w:pos="6803" */
  text-align: right;
}
```

**Reportlab / WeasyPrint** (Python PDF): same mm values as `mm` suffix or as float points (`120 * mm`).

## Edge Cases

| Case | Solution |
|---|---|
| Tab is in `<w:tabs>` in the style, not in the paragraph | search in `word/styles.xml` — mind style inheritance |
| Multiple tabs in one line | order in XML = visual order, `w:val` shows `left/center/right/decimal` |
| Tab in header/footer | `word/header1.xml` / `word/footer1.xml` have their own XML tree |
| Section-specific measurements | `<w:sectPr>` at the end of a section — separate pgMar per section |
| Custom units (e.g. mm directly) | rare; mind `w:val="..."` validator attributes |

## Anti-Patterns

| Anti-Pattern | Why it's bad |
|---|---|
| Estimating visually from a PDF screenshot | ±5mm error, format drift on print |
| Opening Word + using the ruler tool | slow, not reproducible, no audit log |
| Asking AI for typical DIN-5008 values | DIN 5008 has ranges; the reference letter has CONCRETE values. Concrete > generic. |
| Markdown frontmatter with only partial layout | half is right, the other half guessed — inconsistency |

## Cost of NOT extracting

- 2+ hours of iterations on "does the date fit now?", "tab right or center?", "12mm or 14mm spacing?"
- 5+ deploy rounds, each requiring a visual review
- The reference letter held all values: `w:pos="6803"` = 120mm, date at the bottom next to the greeting line, recipient directly after the header
- Investing 5 minutes up front with `unzip + grep` would have made the day 2h shorter

## Promotion Checklist (DRAFT → GA)

- [ ] RED subagent: give a reference DOCX + task "replicate layout in HTML", without skill → measure pixel deviation
- [ ] GREEN subagent: same task with skill → measure deviation
- [ ] Edge case: section-specific pgMar in a multi-page letter
- [ ] CSO check: does "layout like my old letter" trigger reliably?
