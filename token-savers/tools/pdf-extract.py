#!/usr/bin/env python3
"""pdf-extract.py — Windows-friendly PDF text extraction without a system binary.

Purpose: mirror the `pdftotext` / `pdfinfo` (poppler-utils) workflow used by the
`pdf-text-extract-without-vision` skill, but using a pure-Python PDF library
(PyMuPDF / `fitz`) instead of a compiled system binary. poppler-utils is a
Homebrew-only install on macOS; on Windows there is no equivalent one-liner
that works reliably without admin rights, so this tool replaces the binary
dependency entirely. No system binary, no admin rights, no PATH juggling —
just `pip install pymupdf`.

Usage (mirrors pdftotext/pdfinfo flags 1:1 where practical):

    pdf-extract.py info <file.pdf>
        # like `pdfinfo` — page count, size, metadata, per-page dimensions

    pdf-extract.py text <file.pdf> [--out PATH] [-f N] [-l M]
        # like `pdftotext -nopgbrk` — flat UTF-8 text, no page-break markers

    pdf-extract.py text <file.pdf> --layout [--out PATH]
        # like `pdftotext -layout` — preserves column/table whitespace layout

    pdf-extract.py text <file.pdf> --pages [--out PATH]
        # like plain `pdftotext` — keeps \\f form-feed page separators

    pdf-extract.py probe <file.pdf>
        # quick text-layer probe (first ~20 lines) — is this a scanned PDF?

Dependencies:
- PyMuPDF (`pip install pymupdf`) — pure wheel, no system binary required.

Exit codes: 0 ok, 2 file not found, 3 PyMuPDF missing, 4 open/parse error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows: default stdout/stderr encoding follows the system ANSI codepage
# (e.g. cp1252), which silently mangles non-ASCII output (umlauts, em-dash,
# accented names) even though it never raises. Force UTF-8 unconditionally.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _require_pymupdf():
    try:
        import pymupdf as fitz  # noqa: F401  (non-deprecated import name)
    except ImportError:
        try:
            import fitz  # older pymupdf releases only exposed this name
        except ImportError:
            print(
                "ERROR: PyMuPDF is required for this tool.\n"
                "Install via:\n"
                "  python -m pip install pymupdf\n"
                "(pure wheel — no admin rights, no system binary, works identically "
                "on Windows/macOS/Linux)",
                file=sys.stderr,
            )
            sys.exit(3)
    return fitz


def _open(fitz, path: Path):
    try:
        return fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not open PDF: {exc}", file=sys.stderr)
        sys.exit(4)


# ──────────────────────────────────────────────────────────────────────────
# info — like `pdfinfo`
# ──────────────────────────────────────────────────────────────────────────


def cmd_info(args: argparse.Namespace) -> int:
    fitz = _require_pymupdf()
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    doc = _open(fitz, src)
    meta = doc.metadata or {}
    page0 = doc[0] if doc.page_count else None
    page_size = None
    if page0 is not None:
        r = page0.rect
        page_size = {"width_pts": round(r.width, 1), "height_pts": round(r.height, 1)}

    # Rough text-layer check: does ANY page yield extractable text?
    has_text_layer = False
    for p in doc:
        if p.get_text("text").strip():
            has_text_layer = True
            break

    report = {
        "file": str(src),
        "pages": doc.page_count,
        "file_size_bytes": src.stat().st_size,
        "page_size": page_size,
        "encrypted": doc.is_encrypted,
        "has_text_layer": has_text_layer,
        "title": meta.get("title") or None,
        "author": meta.get("author") or None,
        "producer": meta.get("producer") or None,
        "creation_date": meta.get("creationDate") or None,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    doc.close()
    return 0


# ──────────────────────────────────────────────────────────────────────────
# probe — quick text-layer sanity check
# ──────────────────────────────────────────────────────────────────────────


def cmd_probe(args: argparse.Namespace) -> int:
    fitz = _require_pymupdf()
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    doc = _open(fitz, src)
    first_page_text = doc[0].get_text("text") if doc.page_count else ""
    lines = [l for l in first_page_text.splitlines() if l.strip()]
    preview = "\n".join(lines[:20])

    if not preview.strip():
        print(
            "[no extractable text on page 1 — likely a scanned/image-only PDF]\n"
            "Fall back to OCR: img-preprocess.py ocr (after rasterizing pages) "
            "or Claude Vision.",
            file=sys.stderr,
        )
        doc.close()
        return 1

    print(preview)
    doc.close()
    return 0


# ──────────────────────────────────────────────────────────────────────────
# text — like `pdftotext` (with -layout / -nopgbrk / -f/-l equivalents)
# ──────────────────────────────────────────────────────────────────────────


def cmd_text(args: argparse.Namespace) -> int:
    fitz = _require_pymupdf()
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    doc = _open(fitz, src)
    n = doc.page_count
    first = (args.first - 1) if args.first else 0
    last = args.last if args.last else n
    first = max(0, first)
    last = min(n, last)

    mode = "blocks-layout" if args.layout else "plain"
    chunks = []
    for i in range(first, last):
        page = doc[i]
        if args.layout:
            # PyMuPDF's "text" extraction already preserves reading order well;
            # for column/table-ish preservation we additionally sort blocks by
            # position and pad with the built-in whitespace-preserving mode.
            text = page.get_text("text", sort=True)
        else:
            text = page.get_text("text")
        chunks.append(text.rstrip("\n"))

    if args.pages:
        # Like plain `pdftotext`: \f page separators, no trailing strip
        body = "\f".join(chunks)
    else:
        # Like `pdftotext -nopgbrk`: flat text, blank line between pages
        body = "\n\n".join(chunks)

    doc.close()

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(body, encoding="utf-8")
        print(json.dumps({
            "file": str(src),
            "out": str(out_path),
            "pages_extracted": last - first,
            "mode": mode,
            "char_count": len(body),
        }, indent=2))
    else:
        sys.stdout.write(body)
        if not body.endswith("\n"):
            sys.stdout.write("\n")
    return 0


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pdf-extract",
        description="Extract PDF text without Claude Vision and without a "
                     "system pdftotext/poppler binary (pure-Python, PyMuPDF).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="Metadata probe (like `pdfinfo`)")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("probe", help="Quick text-layer check (first ~20 lines of page 1)")
    p.add_argument("file")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("text", help="Full text extraction (like `pdftotext`)")
    p.add_argument("file")
    p.add_argument("--out", help="write to this path instead of stdout")
    p.add_argument("--layout", action="store_true",
                    help="preserve table/column layout (like `pdftotext -layout`)")
    p.add_argument("--pages", action="store_true",
                    help="keep \\f page-break separators (like plain `pdftotext`, "
                         "without this flag behaves like `-nopgbrk`)")
    p.add_argument("-f", "--first", type=int, default=None, help="first page (1-based)")
    p.add_argument("-l", "--last", type=int, default=None, help="last page (1-based)")
    p.set_defaults(func=cmd_text)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
