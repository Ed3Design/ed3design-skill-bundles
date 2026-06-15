#!/usr/bin/env python3
"""img-preprocess.py — Pre-process images before Claude Vision API.

Token-saving wrapper for trading / maker engineering sessions.

Pattern (Sprint 2 Item 5 aus token-optimierung-Roadmap, 12.06.2026):
- Resize zu Vision-API-Schwellen (~1024×1024) statt Originals (~3000×4000)
  → ~6-9× weniger Pixel = ~75-85% weniger Vision-Tokens
- EXIF extrahieren als Markdown statt full-image für Metadata-Queries
- OCR via Tesseract wenn Text-only-Extraktion reicht (kein Vision nötig)
- Color-Histogramm für Brand-/Design-Reviews (3-5 dominant colors statt Pixel-Grid)

Usage:
    img-preprocess.py resize <file> [--max 1024] [--quality 85] [--out PATH]
    img-preprocess.py info <file>           # EXIF + dimensions + size summary
    img-preprocess.py ocr <file>            # Tesseract OCR (graceful fallback)
    img-preprocess.py describe <file>       # info + ocr-summary in einem Schritt
    img-preprocess.py colors <file> [--n 5] # Dominant colors

Dependencies (lokal vorhanden, 12.06. verifiziert):
- Pillow (PIL) 12.1.1+
- ImageMagick `convert` (optional, für extreme HEIC-Conversions)
- Tesseract (optional, fallback wenn nicht installiert)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    print("ERROR: Pillow (PIL) nicht installiert. pip install Pillow", file=sys.stderr)
    sys.exit(2)


# ──────────────────────────────────────────────────────────────────────────
# resize
# ──────────────────────────────────────────────────────────────────────────


def cmd_resize(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    out = Path(args.out) if args.out else src.with_stem(src.stem + "_resized")
    img = Image.open(src)
    orig_size = src.stat().st_size
    orig_dims = img.size

    img.thumbnail((args.max, args.max), Image.Resampling.LANCZOS)

    # JPEG-Quality nur für JPG-Output; PNG ignoriert quality
    save_kwargs = {}
    if out.suffix.lower() in (".jpg", ".jpeg"):
        save_kwargs["quality"] = args.quality
        save_kwargs["optimize"] = True
        if img.mode != "RGB":
            img = img.convert("RGB")
    elif out.suffix.lower() == ".png":
        save_kwargs["optimize"] = True

    img.save(out, **save_kwargs)
    new_size = out.stat().st_size
    saving_pct = round((1 - new_size / orig_size) * 100, 1) if orig_size else 0

    report = {
        "src": str(src),
        "out": str(out),
        "orig_dims": orig_dims,
        "new_dims": img.size,
        "orig_size_kb": round(orig_size / 1024, 1),
        "new_size_kb": round(new_size / 1024, 1),
        "saving_pct": saving_pct,
    }
    print(json.dumps(report, indent=2))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# info — EXIF + dimensions + size
# ──────────────────────────────────────────────────────────────────────────


_INTERESTING_EXIF_KEYS = {
    "DateTime", "DateTimeOriginal", "DateTimeDigitized",
    "Make", "Model", "LensModel",
    "FocalLength", "FNumber", "ExposureTime", "ISOSpeedRatings",
    "ImageWidth", "ImageLength",
    "Software", "Artist", "Copyright",
    "GPSInfo",
}


def cmd_info(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    img = Image.open(src)
    exif_raw = img.getexif() if hasattr(img, "getexif") else {}

    exif_clean: dict[str, str] = {}
    for tag_id, value in exif_raw.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        if tag_name in _INTERESTING_EXIF_KEYS:
            # GPSInfo ist ein Sub-Dict — bei Bedarf separat decoden
            try:
                exif_clean[tag_name] = str(value)[:100]
            except Exception:
                pass

    report = {
        "file": str(src),
        "format": img.format,
        "mode": img.mode,
        "dimensions": img.size,
        "size_kb": round(src.stat().st_size / 1024, 1),
        "exif": exif_clean,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# ocr — Tesseract (graceful fallback)
# ──────────────────────────────────────────────────────────────────────────


def cmd_ocr(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    tesseract = shutil.which("tesseract")
    if tesseract is None:
        print(
            "ERROR: tesseract nicht installiert.\n"
            "Install: brew install tesseract tesseract-lang\n"
            "Alternative: img-preprocess.py resize <file> dann via Claude Vision.",
            file=sys.stderr,
        )
        return 3

    try:
        proc = subprocess.run(
            [tesseract, str(src), "-", "-l", args.lang],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("ERROR: tesseract timeout (30s)", file=sys.stderr)
        return 4

    if proc.returncode != 0:
        print(f"ERROR: tesseract returned {proc.returncode}: {proc.stderr.strip()}",
              file=sys.stderr)
        return 5

    text = proc.stdout.strip()
    report = {
        "file": str(src),
        "lang": args.lang,
        "char_count": len(text),
        "line_count": len(text.split("\n")),
        "text": text,
    }
    print(json.dumps(report, indent=2, default=str))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# describe — info + ocr-preview in einem Pipe
# ──────────────────────────────────────────────────────────────────────────


def cmd_describe(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    img = Image.open(src)
    exif_raw = img.getexif() if hasattr(img, "getexif") else {}
    exif_clean = {
        ExifTags.TAGS.get(tag_id, str(tag_id)): str(value)[:100]
        for tag_id, value in exif_raw.items()
        if ExifTags.TAGS.get(tag_id) in _INTERESTING_EXIF_KEYS
    }

    out: dict = {
        "file": str(src),
        "format": img.format,
        "dimensions": img.size,
        "size_kb": round(src.stat().st_size / 1024, 1),
        "exif_summary": exif_clean,
    }

    tesseract = shutil.which("tesseract")
    if tesseract:
        try:
            proc = subprocess.run(
                [tesseract, str(src), "-", "-l", args.lang],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                text = proc.stdout.strip()
                preview = text[: args.preview]
                if len(text) > args.preview:
                    preview += f"... [+{len(text) - args.preview} chars]"
                out["ocr_preview"] = preview
                out["ocr_char_count"] = len(text)
        except subprocess.TimeoutExpired:
            out["ocr_preview"] = "[OCR timeout]"
    else:
        out["ocr_preview"] = (
            "[tesseract nicht installiert — brew install tesseract tesseract-lang]"
        )

    print(json.dumps(out, indent=2, default=str))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# colors — dominant colors via PIL quantize
# ──────────────────────────────────────────────────────────────────────────


def cmd_colors(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 2

    img = Image.open(src).convert("RGB")
    img.thumbnail((200, 200), Image.Resampling.LANCZOS)  # speed
    quant = img.quantize(colors=args.n)
    palette = quant.getpalette()[: args.n * 3]
    counts = Counter(quant.getdata())

    colors = []
    for idx, count in counts.most_common(args.n):
        r, g, b = palette[idx * 3 : idx * 3 + 3]
        colors.append({
            "rgb": f"#{r:02x}{g:02x}{b:02x}",
            "pct": round(count / quant.size[0] / quant.size[1] * 100, 1),
        })

    report = {
        "file": str(src),
        "n_requested": args.n,
        "n_found": len(colors),
        "dominant_colors": colors,
    }
    print(json.dumps(report, indent=2))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="img-preprocess",
        description="Pre-process images to reduce Claude Vision token costs.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("resize", help="Resize image to max dimension")
    p.add_argument("file")
    p.add_argument("--max", type=int, default=1024, help="max dim (default 1024)")
    p.add_argument("--quality", type=int, default=85, help="JPEG quality 1-100")
    p.add_argument("--out", help="output path (default: <stem>_resized<ext>)")
    p.set_defaults(func=cmd_resize)

    p = sub.add_parser("info", help="EXIF + dimensions + size summary")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("ocr", help="OCR via Tesseract")
    p.add_argument("file")
    p.add_argument("--lang", default="deu+eng", help="Tesseract lang (default deu+eng)")
    p.set_defaults(func=cmd_ocr)

    p = sub.add_parser("describe", help="EXIF + dimensions + OCR-preview in one call")
    p.add_argument("file")
    p.add_argument("--lang", default="deu+eng")
    p.add_argument("--preview", type=int, default=500, help="OCR preview char count")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("colors", help="Dominant colors via quantize")
    p.add_argument("file")
    p.add_argument("--n", type=int, default=5, help="number of colors")
    p.set_defaults(func=cmd_colors)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
