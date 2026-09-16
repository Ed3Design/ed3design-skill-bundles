#!/usr/bin/env python3
"""img-preprocess.py — Pre-process images before Claude Vision API.

Token-saving wrapper for trading / maker engineering sessions.

Pattern:
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

Dependencies:
- Pillow (PIL) >= 10.0 — required for resize/info/describe/colors subcommands
- Tesseract (optional, system binary) — for `ocr` subcommand
  - macOS: `brew install tesseract tesseract-lang`
  - Windows: `winget install --id UB-Mannheim.TesseractOCR -e --silent
    --accept-package-agreements --accept-source-agreements` (per-user install,
    no admin needed). This tool auto-detects the winget/manual install
    locations even when tesseract isn't on PATH yet, and falls back to
    whatever language packs are actually installed instead of hard-failing.
- ImageMagick `convert` (optional) — for extreme HEIC-conversions outside Pillow's scope
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Windows: default stdout/stderr encoding follows the system ANSI codepage
# (e.g. cp1252), which silently mangles non-ASCII output (umlauts, em-dash,
# accented names) even though it never raises. Force UTF-8 unconditionally.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────────────────
# tesseract lookup (cross-platform)
# ──────────────────────────────────────────────────────────────────────────
#
# On macOS `brew install tesseract` puts the binary on PATH. On Windows the
# common installers (winget UB-Mannheim.TesseractOCR, or the manual UB-Mannheim
# .exe installer) do NOT reliably add themselves to PATH for the current
# session/shell — so `shutil.which` alone often misses a real install. Check a
# handful of well-known install locations as a fallback before giving up.

_WINDOWS_TESSERACT_CANDIDATES = [
    r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",   # winget (user scope)
    r"%ProgramFiles%\Tesseract-OCR\tesseract.exe",              # manual installer (machine scope)
    r"%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe",
]


def _find_tesseract() -> str | None:
    """Return a usable tesseract executable path, or None if not found."""
    env_override = os.environ.get("TESSERACT_PATH")
    if env_override and Path(env_override).exists():
        return env_override

    found = shutil.which("tesseract")
    if found:
        return found

    if sys.platform == "win32":
        for template in _WINDOWS_TESSERACT_CANDIDATES:
            candidate = Path(os.path.expandvars(template))
            if candidate.exists():
                return str(candidate)
    return None


def _tesseract_install_hint() -> str:
    if sys.platform == "win32":
        return (
            "ERROR: tesseract not found.\n"
            "Install (no admin required, per-user install):\n"
            "  winget install --id UB-Mannheim.TesseractOCR -e --silent \\\n"
            "      --accept-package-agreements --accept-source-agreements\n"
            "  # installs to %LOCALAPPDATA%\\Programs\\Tesseract-OCR — this tool "
            "auto-detects that path.\n"
            "If winget is unavailable or blocked, download the installer manually:\n"
            "  https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  (UB-Mannheim Windows build; run the .exe, no admin needed for a "
            "per-user install)\n"
            "Alternative: img-preprocess.py resize <file> then send via Claude Vision."
        )
    return (
        "ERROR: tesseract nicht installiert.\n"
        "Install: brew install tesseract tesseract-lang\n"
        "Alternative: img-preprocess.py resize <file> dann via Claude Vision."
    )


def _available_tesseract_langs(tesseract_path: str) -> set[str]:
    """Best-effort: parse `tesseract --list-langs` output."""
    try:
        proc = subprocess.run(
            [tesseract_path, "--list-langs"],
            capture_output=True, text=True, timeout=10,
        )
        langs = set()
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line and "list of" not in line.lower():
                langs.add(line)
        return langs
    except Exception:
        return set()


def _resolve_lang(tesseract_path: str, requested: str) -> tuple[str, str | None]:
    """Resolve a requested Tesseract --lang value against what's actually
    installed (e.g. only 'eng' present on a fresh Windows install that lacks
    the German language pack). Returns (lang_to_use, warning_or_None)."""
    available = _available_tesseract_langs(tesseract_path)
    if not available:
        # couldn't introspect — just pass the request through as-is
        return requested, None

    requested_parts = requested.split("+")
    usable = [p for p in requested_parts if p in available]
    if usable == requested_parts:
        return requested, None
    if usable:
        return "+".join(usable), (
            f"[some requested languages not installed: "
            f"{sorted(set(requested_parts) - available)}; using {'+'.join(usable)}]"
        )
    # nothing requested is available — fall back to whatever IS there
    fallback = "eng" if "eng" in available else sorted(available)[0]
    return fallback, (
        f"[none of requested languages {requested_parts} installed "
        f"(have: {sorted(available)}); falling back to '{fallback}'. "
        f"Install more via: winget install --id UB-Mannheim.TesseractOCR "
        f"or rerun the installer and pick additional language components.]"
    )

# Pillow is imported lazily INSIDE the subcommands that need it, so that
# `img-preprocess.py --help` works even on a system without Pillow.
# Each subcommand calls `_require_pillow()` at entry.


def _require_pillow():
    """Import PIL lazily; print a clear hint if missing."""
    try:
        from PIL import Image, ExifTags  # noqa: F401
    except ImportError:
        print(
            "ERROR: Pillow (PIL) is required for this subcommand.\n"
            "Install via:\n"
            "  pip install Pillow\n"
            "  # or: pip install '.[token-savers]' from the bundle repo root",
            file=sys.stderr,
        )
        sys.exit(2)
    from PIL import Image, ExifTags
    return Image, ExifTags


# ──────────────────────────────────────────────────────────────────────────
# resize
# ──────────────────────────────────────────────────────────────────────────


def cmd_resize(args: argparse.Namespace) -> int:
    Image, _ExifTags = _require_pillow()
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
    Image, ExifTags = _require_pillow()
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

    tesseract = _find_tesseract()
    if tesseract is None:
        print(_tesseract_install_hint(), file=sys.stderr)
        return 3

    lang, warning = _resolve_lang(tesseract, args.lang)

    try:
        proc = subprocess.run(
            [tesseract, str(src), "-", "-l", lang],
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
        "lang": lang,
        "requested_lang": args.lang,
        "char_count": len(text),
        "line_count": len(text.split("\n")),
        "text": text,
    }
    if warning:
        report["warning"] = warning
    print(json.dumps(report, indent=2, default=str))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# describe — info + ocr-preview in einem Pipe
# ──────────────────────────────────────────────────────────────────────────


def cmd_describe(args: argparse.Namespace) -> int:
    Image, ExifTags = _require_pillow()
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

    tesseract = _find_tesseract()
    if tesseract:
        lang, warning = _resolve_lang(tesseract, args.lang)
        try:
            proc = subprocess.run(
                [tesseract, str(src), "-", "-l", lang],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode == 0:
                text = proc.stdout.strip()
                preview = text[: args.preview]
                if len(text) > args.preview:
                    preview += f"... [+{len(text) - args.preview} chars]"
                out["ocr_preview"] = preview
                out["ocr_char_count"] = len(text)
                if warning:
                    out["ocr_warning"] = warning
        except subprocess.TimeoutExpired:
            out["ocr_preview"] = "[OCR timeout]"
    else:
        out["ocr_preview"] = "[" + _tesseract_install_hint().replace("\n", " ") + "]"

    print(json.dumps(out, indent=2, default=str))
    return 0


# ──────────────────────────────────────────────────────────────────────────
# colors — dominant colors via PIL quantize
# ──────────────────────────────────────────────────────────────────────────


def cmd_colors(args: argparse.Namespace) -> int:
    Image, _ExifTags = _require_pillow()
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
