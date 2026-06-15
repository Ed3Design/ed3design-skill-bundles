#!/usr/bin/env python3
"""html2md.py — HTML zu Markdown für Token-effiziente Web-Reads.

Pattern derived from token-optimization work.

Pattern: statt WebFetch (full-HTML in Context) URL fetchen → readability-style
content extraction → kompakte Markdown-Konversion. ~60-80% Token-Saving für
Stock3-Artikel, Docs-Pages, Blog-Posts.

Strategy:
1. Content-Extraction via bs4 (entfernt nav/footer/script/style/aside/header)
2. Markdown-Konversion: headings, paragraphs, lists, links, code-blocks, tables
3. Whitespace-Normalisierung + Leerzeilen-Compaction

Optional Best-Quality-Mode: wenn `html2text` installed → benutzt das stattdessen.

Usage:
    html2md.py https://stock3.com/news/article-xyz
    html2md.py path/to/local.html
    html2md.py - < piped.html
    html2md.py URL --raw         # Skip content-extraction, ganze Seite
    html2md.py URL --max-chars 8000  # Truncate-Cap

Output: Markdown auf stdout.

Token-Cost-Schätzung:
- Original-Stock3-Artikel: ~15-25k Tokens HTML
- Nach bs4-Extract + Markdown: ~3-6k Tokens
- Saving: ~70-80%
"""

from __future__ import annotations

import argparse
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

# macOS-Python ships ohne Root-Certs in einigen Setups. Wenn `certifi` installiert ist,
# nutzen wir dessen CA-Bundle (Best Practice). Sonst System-Default — bei Cert-Fehler
# muss User entweder `pip install certifi` oder `/Applications/Python 3.x/Install Certificates.command`
# (macOS-Python-Installer-Script) ausführen. **Niemals** SSL-Verify abschalten (MITM-Risiko).
try:
    import certifi  # type: ignore

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

# ──────────────────────────────────────────────────────────────────────────
# Try optional best-quality libs first
# ──────────────────────────────────────────────────────────────────────────

try:
    import html2text  # type: ignore

    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

try:
    from bs4 import BeautifulSoup, NavigableString  # type: ignore

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ──────────────────────────────────────────────────────────────────────────
# Fetch
# ──────────────────────────────────────────────────────────────────────────

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch URL with browser-like UA."""
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
        raw = resp.read()
        # Try to detect encoding from Content-Type, fallback utf-8
        encoding = "utf-8"
        ctype = resp.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ctype)
        if m:
            encoding = m.group(1)
        try:
            return raw.decode(encoding, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")


def read_input(source: str) -> str:
    """Read HTML from URL, file-path, or stdin (-)."""
    if source == "-":
        return sys.stdin.read()
    if source.startswith("http://") or source.startswith("https://"):
        return fetch_url(source)
    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Kein File: {source}")
    return path.read_text(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────────────────────────────────
# Content-Extraction (bs4-based, no readability dep needed)
# ──────────────────────────────────────────────────────────────────────────

NOISE_TAGS = ["script", "style", "nav", "footer", "aside", "header", "noscript", "iframe", "form"]
NOISE_CLASS_PATTERNS = re.compile(
    r"\b(cookie|consent|banner|popup|modal|advertisement|sidebar|nav|footer|"
    r"social|share|comment|related|recommended|newsletter)\b",
    re.IGNORECASE,
)


def extract_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """Heuristisches main-content extraction.

    Strategy:
    1. Remove obvious noise tags (script/style/nav/footer/aside/header)
    2. Remove elements with noisy class/id (cookie, banner, sidebar, etc.)
    3. Prefer <main>, <article>, or div mit `id*=content|main|article`
    """
    # Step 1: strip noise tags
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Step 2: strip noise-classed elements
    for tag in soup.find_all(class_=NOISE_CLASS_PATTERNS):
        tag.decompose()
    for tag in soup.find_all(id=NOISE_CLASS_PATTERNS):
        tag.decompose()

    # Step 3: prefer semantic main content
    main = soup.find("main") or soup.find("article")
    if main:
        return main

    # Fallback: search for content-marked div
    for div in soup.find_all("div", id=re.compile(r"content|main|article", re.IGNORECASE)):
        return div
    for div in soup.find_all("div", class_=re.compile(r"content|main|article", re.IGNORECASE)):
        return div

    # Last fallback: body
    body = soup.find("body")
    return body if body else soup


# ──────────────────────────────────────────────────────────────────────────
# HTML → Markdown Konvertierung (bs4-based)
# ──────────────────────────────────────────────────────────────────────────


def convert_to_markdown(element) -> str:
    """Rekursive HTML→Markdown-Konversion."""
    if isinstance(element, NavigableString):
        # Keep original whitespace (Tag-Boundaries brauchen Spaces),
        # nur Multi-Newlines werden später in normalize_whitespace gekollabiert
        return str(element)

    name = element.name
    if name is None:
        return ""

    # Recursive children
    children_md = "".join(convert_to_markdown(c) for c in element.children)

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        return f"\n\n{'#' * level} {children_md.strip()}\n\n"

    if name == "p":
        return f"\n\n{children_md.strip()}\n\n"

    if name in ("strong", "b"):
        return f"**{children_md.strip()}**"

    if name in ("em", "i"):
        return f"*{children_md.strip()}*"

    if name == "code":
        # Inline code
        return f"`{children_md.strip()}`"

    if name == "pre":
        # Code-block
        return f"\n\n```\n{element.get_text()}\n```\n\n"

    if name == "a":
        href = element.get("href", "")
        text = children_md.strip() or href
        if href:
            return f"[{text}]({href})"
        return text

    if name == "br":
        return "\n"

    if name == "hr":
        return "\n\n---\n\n"

    if name == "ul":
        items = [convert_to_markdown(li).strip() for li in element.find_all("li", recursive=False)]
        return "\n\n" + "\n".join(f"- {it}" for it in items if it) + "\n\n"

    if name == "ol":
        items = [convert_to_markdown(li).strip() for li in element.find_all("li", recursive=False)]
        return "\n\n" + "\n".join(f"{i+1}. {it}" for i, it in enumerate(items) if it) + "\n\n"

    if name == "li":
        return children_md.strip()

    if name == "blockquote":
        lines = children_md.strip().split("\n")
        return "\n\n" + "\n".join(f"> {ln}" for ln in lines) + "\n\n"

    if name == "table":
        # Vereinfachte Markdown-Tabelle
        rows = element.find_all("tr")
        if not rows:
            return ""
        md_rows = []
        for i, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [c.get_text().strip().replace("|", "\\|") for c in cells]
            md_rows.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                md_rows.append("| " + " | ".join("---" for _ in cells) + " |")
        return "\n\n" + "\n".join(md_rows) + "\n\n"

    if name == "img":
        alt = element.get("alt", "")
        src = element.get("src", "")
        return f"![{alt}]({src})" if src else f"({alt})"

    # Default: pass through children
    return children_md


# ──────────────────────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────────────────────


def normalize_whitespace(md: str) -> str:
    """Kollabiere multiple Leerzeilen, trim, dedupliziere whitespace."""
    # Mehr als 2 Leerzeilen → 2
    md = re.sub(r"\n{3,}", "\n\n", md)
    # Multiple Spaces in einer Zeile → 1
    md = re.sub(r"[ \t]+", " ", md)
    # Leading/trailing whitespace pro Zeile
    md = "\n".join(line.rstrip() for line in md.split("\n"))
    return md.strip()


# ──────────────────────────────────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────────────────────────────────


def html_to_markdown(html: str, raw: bool = False) -> str:
    """Convert HTML to Markdown via best available path."""
    # Optional best-quality path
    if HAS_HTML2TEXT and not raw:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # no wrap
        # First strip noise via bs4 if available, then html2text
        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            content = extract_main_content(soup)
            return normalize_whitespace(h.handle(str(content)))
        return normalize_whitespace(h.handle(html))

    # Pure-bs4 path
    if not HAS_BS4:
        # Last-resort regex strip (very basic)
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return normalize_whitespace(text)

    soup = BeautifulSoup(html, "html.parser")
    content = soup if raw else extract_main_content(soup)
    md = convert_to_markdown(content)
    return normalize_whitespace(md)


def main() -> int:
    p = argparse.ArgumentParser(
        description="HTML zu Markdown für Token-effiziente Web-Reads."
    )
    p.add_argument(
        "source",
        help="URL, lokaler Pfad, oder '-' für stdin",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="Skip content-extraction, ganzes Dokument konvertieren",
    )
    p.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Truncate-Cap (z.B. 8000 für ~2k Tokens)",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print Konversions-Stats nach stderr (orig/result chars + saving)",
    )
    args = p.parse_args()

    try:
        html = read_input(args.source)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in msg:
            print(
                "Error: SSL-Cert-Verify fehlgeschlagen. Fix-Optionen:\n"
                "  (a) pip install certifi   (Best Practice)\n"
                "  (b) /Applications/Python\\ 3.x/Install\\ Certificates.command   (macOS-Bundle)\n"
                "Niemals SSL-Verify abschalten (MITM-Risiko).",
                file=sys.stderr,
            )
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    original_chars = len(html)
    md = html_to_markdown(html, raw=args.raw)

    if args.max_chars and len(md) > args.max_chars:
        md = md[: args.max_chars] + "\n\n[... truncated]"

    print(md)

    if args.stats:
        result_chars = len(md)
        saving = 100 * (1 - result_chars / original_chars) if original_chars > 0 else 0
        print(
            f"\nStats (stderr): {original_chars} chars HTML → "
            f"{result_chars} chars MD ({saving:.1f}% saving)",
            file=sys.stderr,
        )
        engine = "html2text+bs4" if HAS_HTML2TEXT else "bs4-only"
        print(f"Engine: {engine}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
