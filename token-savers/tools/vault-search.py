#!/usr/bin/env python3
"""vault-search.py — Single-call Vault-Search mit Smart-Ranking.

Sprint 2 Item 6a aus token-optimierung-Roadmap (12.06.2026).

Pattern: statt 2-3 separater Glob+Grep-Calls vor jedem Vault-First-Check
ein einziger Tool-Call der Top-N wahrscheinlich-relevante Notes liefert
mit Relevanz-Score + 2-Line-Excerpt.

Ranking-Heuristik:
- Filename-Match: +5 pro Query-Wort im Filename (case-insensitive)
- Heading-Match (H1/H2/H3): +3 pro Match
- Content-Match: +1 pro Vorkommen
- Frontmatter-Tag-Match: +4
- Recent-File-Boost: +0.5 pro Monat seit Erstellung (max +6)

Output: JSON mit ranked Top-N (default 5) + 2-Line-Excerpt pro Match.

Usage:
    vault-search.py "token optimierung" [--max 5] [--excerpt-lines 2]
    vault-search.py "trading ko-schein" --scope projekte
    vault-search.py "verhandlung" --include-archiv

Scope-Pre-Sets:
    --scope projekte    → 02 Projekte/
    --scope bereiche    → 03 Bereiche/
    --scope ressourcen  → 04 Ressourcen/
    --scope daily       → 05 Daily Notes/
    --scope all         → alle (außer 06 Archiv unless --include-archiv)

Default-Vault: ~/Documents/Vault/ClaudetteV/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────

DEFAULT_VAULT = Path.home() / "Documents" / "Vault" / "ClaudetteV"
SCOPES = {
    "projekte": ["02 Projekte"],
    "bereiche": ["03 Bereiche"],
    "ressourcen": ["04 Ressourcen"],
    "daily": ["05 Daily Notes"],
    "inbox": ["01 Inbox"],
    "kontext": ["00 Kontext"],
    "all": [
        "00 Kontext", "01 Inbox", "02 Projekte",
        "03 Bereiche", "04 Ressourcen", "05 Daily Notes",
    ],
}

# Ranking-Gewichte
W_FILENAME = 5.0
W_HEADING = 3.0
W_CONTENT = 1.0
W_TAG = 4.0
W_RECENT_PER_MONTH = 0.5
W_RECENT_CAP = 6.0


# ──────────────────────────────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────────────────────────────


def _tokenize_query(query: str) -> list[str]:
    """Lowercase + split on whitespace + filter trivial words."""
    words = re.findall(r"\w+", query.lower())
    stopwords = {"in", "im", "an", "auf", "und", "oder", "the", "and", "or"}
    return [w for w in words if w not in stopwords and len(w) >= 2]


def _file_age_months(path: Path) -> float:
    """Months since mtime (approximate, 30d-month)."""
    age_s = time.time() - path.stat().st_mtime
    return age_s / (86400 * 30)


def _extract_excerpts(
    content: str, query_words: list[str], n_lines: int = 2
) -> list[str]:
    """Return up to n_lines lines containing query words, with context."""
    lines = content.split("\n")
    excerpts: list[str] = []
    for i, line in enumerate(lines):
        ll = line.lower()
        if any(w in ll for w in query_words):
            excerpts.append(line.strip()[:160])
            if len(excerpts) >= n_lines:
                break
    return excerpts


def _score_file(
    path: Path, content: str, query_words: list[str]
) -> tuple[float, dict]:
    """Compute relevance score + breakdown."""
    score = 0.0
    breakdown = {
        "filename": 0,
        "heading": 0,
        "content": 0,
        "tag": 0,
        "recency": 0.0,
    }

    fname_lower = path.name.lower()
    for w in query_words:
        if w in fname_lower:
            score += W_FILENAME
            breakdown["filename"] += 1

    content_lower = content.lower()
    # Heading-Matches (Markdown #, ##, ###)
    heading_re = re.compile(r"^#+\s+(.*)$", re.MULTILINE)
    for h_match in heading_re.finditer(content_lower):
        h_text = h_match.group(1)
        for w in query_words:
            if w in h_text:
                score += W_HEADING
                breakdown["heading"] += 1

    # Content-Matches (all occurrences, beyond headings)
    for w in query_words:
        cnt = content_lower.count(w)
        if cnt > 0:
            score += cnt * W_CONTENT
            breakdown["content"] += cnt

    # Frontmatter-Tags
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1).lower()
        for w in query_words:
            if w in fm_text:
                score += W_TAG
                breakdown["tag"] += 1

    # Recency-Boost
    age_months = _file_age_months(path)
    recency = max(0, W_RECENT_CAP - age_months * W_RECENT_PER_MONTH)
    score += recency
    breakdown["recency"] = round(recency, 2)

    return score, breakdown


def search(
    vault_root: Path,
    query: str,
    scopes: list[str],
    max_results: int,
    excerpt_lines: int,
) -> dict:
    query_words = _tokenize_query(query)
    if not query_words:
        return {"error": "Query muss mindestens ein 2+-Char-Wort enthalten"}

    candidates: list[tuple[float, Path, dict, list[str]]] = []

    for scope_folder in scopes:
        scope_path = vault_root / scope_folder
        if not scope_path.exists():
            continue
        for md_file in scope_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            score, breakdown = _score_file(md_file, content, query_words)
            if score <= W_RECENT_CAP:
                # Nur Recency-Match, kein Content/Heading/Filename → skip
                continue
            excerpts = _extract_excerpts(content, query_words, excerpt_lines)
            candidates.append((score, md_file, breakdown, excerpts))

    candidates.sort(key=lambda x: -x[0])
    top = candidates[:max_results]

    return {
        "query": query,
        "query_words": query_words,
        "scopes_searched": scopes,
        "total_candidates": len(candidates),
        "returned": len(top),
        "results": [
            {
                "rank": i + 1,
                "score": round(score, 2),
                "wikilink": f"[[{md.relative_to(vault_root).with_suffix('').as_posix()}]]",
                "path_rel": str(md.relative_to(vault_root)),
                "breakdown": breakdown,
                "excerpts": excerpts,
            }
            for i, (score, md, breakdown, excerpts) in enumerate(top)
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vault-search",
        description="Single-call Vault-Search mit Smart-Ranking.",
    )
    parser.add_argument("query", help="Search query (multi-word OK)")
    parser.add_argument(
        "--scope", choices=list(SCOPES.keys()), default="all",
        help="Search-Scope-Preset (default: all außer 06 Archiv)",
    )
    parser.add_argument(
        "--include-archiv", action="store_true",
        help="Auch 06 Archiv durchsuchen",
    )
    parser.add_argument("--max", type=int, default=5, help="Max results (default 5)")
    parser.add_argument(
        "--excerpt-lines", type=int, default=2,
        help="Excerpt-Zeilen pro Treffer (default 2)",
    )
    parser.add_argument(
        "--vault", default=str(DEFAULT_VAULT),
        help=f"Vault-Root (default: {DEFAULT_VAULT})",
    )

    args = parser.parse_args()

    vault_root = Path(args.vault)
    if not vault_root.exists():
        print(f"ERROR: Vault-Root nicht gefunden: {vault_root}", file=sys.stderr)
        return 2

    scopes = list(SCOPES[args.scope])
    if args.include_archiv:
        scopes.append("06 Archiv")

    result = search(
        vault_root=vault_root,
        query=args.query,
        scopes=scopes,
        max_results=args.max,
        excerpt_lines=args.excerpt_lines,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
