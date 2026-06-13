#!/usr/bin/env python3
"""vault-search.py — Single-call vault search with smart ranking.

Pattern: instead of 2-3 separate Glob+Grep calls before each vault-first check,
one tool call that returns top-N likely-relevant notes with relevance score +
2-line excerpts.

Ranking heuristic:
- Filename match: +5 per query word in filename (case-insensitive)
- Heading match (H1/H2/H3): +3 per match
- Content match: +1 per occurrence
- Frontmatter tag match: +4
- Recent file boost: +0.5 per month since creation (max +6)

Output: JSON with ranked top-N (default 5) + 2-line excerpt per match.

Usage:
    vault-search.py "query words" [--max 5] [--excerpt-lines 2]
    vault-search.py "query" --scope <custom-scope>
    vault-search.py "query" --vault /path/to/vault   # override config
    vault-search.py --init                            # write example config

Configuration:
    Reads ~/.config/vault-search/config.json. Example:

    {
      "vault_path": "~/Documents/MyVault",
      "scopes": {
        "projects": ["02 Projects"],
        "daily": ["05 Daily Notes"],
        "all": ["01 Inbox", "02 Projects", "05 Daily Notes"]
      },
      "default_scope": "all",
      "exclude_dirs": [".git", ".obsidian", "node_modules"]
    }

    Or use --vault PATH to override on the command line.
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
# Config loading
# ──────────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".config" / "vault-search" / "config.json"

EXAMPLE_CONFIG = {
    "vault_path": "~/Documents/MyVault",
    "scopes": {
        "projects": ["02 Projects"],
        "areas": ["03 Areas"],
        "resources": ["04 Resources"],
        "daily": ["05 Daily Notes"],
        "inbox": ["01 Inbox"],
        "all": [
            "01 Inbox", "02 Projects", "03 Areas",
            "04 Resources", "05 Daily Notes",
        ],
    },
    "default_scope": "all",
    "exclude_dirs": [".git", ".obsidian", "node_modules"],
}


def load_config() -> dict:
    """Load config from ~/.config/vault-search/config.json or return empty dict."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠ Config-load error: {e}", file=sys.stderr)
        return {}


def init_config() -> int:
    """Write example config to ~/.config/vault-search/config.json."""
    if CONFIG_PATH.exists():
        print(f"Config already exists: {CONFIG_PATH}", file=sys.stderr)
        print("Delete it first if you want to recreate.", file=sys.stderr)
        return 1
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(EXAMPLE_CONFIG, indent=2))
    print(f"✅ Example config written to {CONFIG_PATH}")
    print("   Edit vault_path + scopes for your vault setup.")
    return 0


CONFIG = load_config()

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
        description="Single-call vault search with smart ranking.",
    )
    parser.add_argument("query", nargs="?", help="Search query (multi-word OK)")
    parser.add_argument(
        "--init", action="store_true",
        help=f"Write example config to {CONFIG_PATH} and exit",
    )

    # Resolve scopes + default-scope from config
    config_scopes = CONFIG.get("scopes", {})
    default_scope = CONFIG.get("default_scope", "all")
    scope_choices = list(config_scopes.keys()) if config_scopes else None

    parser.add_argument(
        "--scope",
        choices=scope_choices,
        default=default_scope if scope_choices and default_scope in scope_choices else None,
        help=f"Search scope preset (config-defined; default: {default_scope})",
    )
    parser.add_argument("--max", type=int, default=5, help="Max results (default 5)")
    parser.add_argument(
        "--excerpt-lines", type=int, default=2,
        help="Excerpt lines per match (default 2)",
    )
    parser.add_argument(
        "--vault",
        default=os.path.expanduser(CONFIG.get("vault_path", "")) or None,
        help="Override vault root (default from config.json)",
    )

    args = parser.parse_args()

    if args.init:
        return init_config()

    if not args.query:
        parser.error("query is required (or use --init to write example config)")

    if not args.vault:
        print("ERROR: No vault path configured.", file=sys.stderr)
        print(f"  Either: vault-search.py --init   (write example config)", file=sys.stderr)
        print(f"  Or:     vault-search.py --vault /path/to/vault 'query'", file=sys.stderr)
        return 2

    vault_root = Path(args.vault).expanduser()
    if not vault_root.exists():
        print(f"ERROR: Vault root not found: {vault_root}", file=sys.stderr)
        return 2

    # Build scope folder list from config
    if args.scope and args.scope in config_scopes:
        scopes = list(config_scopes[args.scope])
    else:
        # Fallback: scan all folders in vault root (excluding hidden + exclude_dirs)
        exclude = set(CONFIG.get("exclude_dirs", [".git", ".obsidian"]))
        scopes = [
            p.name for p in vault_root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name not in exclude
        ]

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
