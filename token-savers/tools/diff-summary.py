#!/usr/bin/env python3
"""diff-summary.py — Strukturierte Code-Diff-Summary für Code-Review-Vorbereitung.

Sprint 2 Item 5c aus token-optimierung-Roadmap (12.06.2026).

Pattern: statt `git diff --stat HEAD~5..HEAD` Raw-Output mit hunderten Zeilen
ein kompaktes JSON mit per-File LoC + Change-Type-Klassifikation (refactor/feat/fix/test/docs).

Klassifikations-Heuristik (per File-Pfad-Pattern, dann LoC-Ratio):
- `tests/`, `test_*.py`, `*_test.py` → test
- `*.md`, `docs/` → docs
- `migrations/`, `alembic/`, `*.sql` → migration
- `.github/`, `.gitignore`, `pyproject.toml`, `requirements.txt` → chore
- Pure-additions (insertions >> deletions, ratio >5:1) → feat
- Mixed mit hohem deletion-Anteil → refactor
- Wenig LoC + ein File + Keyword „fix"/"bug" im Commit → fix
- Default → feat

Usage:
    diff-summary.py                          # HEAD~1..HEAD (default)
    diff-summary.py HEAD~5..HEAD              # Custom range
    diff-summary.py --repo ~/Documents/Claude-Code/ultimative-platform
    diff-summary.py HEAD~10..HEAD --top 5     # Nur Top-5 grösste Files

Output (JSON):
    {
      "range": "HEAD~5..HEAD",
      "repo": "/path/to/repo",
      "total_insertions": 946,
      "total_deletions": 124,
      "files_changed": 10,
      "by_type": {"feat": 5, "fix": 2, "test": 3},
      "files": [
        {"path": "...", "ins": 280, "del": 12, "type": "feat"},
        ...
      ],
      "commits": [{"sha": "...", "subject": "...", "type": "feat"}, ...]
    }

Token-Cost: ~200-500 Tokens pro Diff vs ~2-5k für Raw-Output. ~80% Saving.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────
# Klassifikations-Heuristik
# ──────────────────────────────────────────────────────────────────────────

PATH_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(^|/)tests?/"), "test"),
    (re.compile(r"(^|/)test_.*\.py$"), "test"),
    (re.compile(r".*_test\.(py|ts|js)$"), "test"),
    (re.compile(r"\.md$"), "docs"),
    (re.compile(r"(^|/)docs?/"), "docs"),
    (re.compile(r"(^|/)(migrations|alembic)/"), "migration"),
    (re.compile(r"\.sql$"), "migration"),
    (re.compile(r"^\.github/"), "chore"),
    (re.compile(r"^\.gitignore$"), "chore"),
    (re.compile(r"^(pyproject\.toml|requirements.*\.txt|package\.json|poetry\.lock|uv\.lock)$"), "chore"),
    (re.compile(r"^Dockerfile"), "chore"),
    (re.compile(r"compose\.ya?ml$"), "chore"),
]

FIX_KEYWORDS = re.compile(r"\b(fix|bug|patch|hotfix|correct|repair)\b", re.IGNORECASE)
FEAT_KEYWORDS = re.compile(r"\b(feat|feature|add|new|implement)\b", re.IGNORECASE)
REFACTOR_KEYWORDS = re.compile(r"\b(refactor|rewrite|cleanup|simplify|extract)\b", re.IGNORECASE)


def classify_file(path: str, ins: int, dele: int) -> str:
    """Path-pattern first, then LoC-ratio fallback."""
    for pattern, kind in PATH_PATTERNS:
        if pattern.search(path):
            return kind

    # LoC-ratio Heuristik
    if dele == 0 and ins > 0:
        return "feat"  # pure addition
    if ins == 0 and dele > 0:
        return "remove"
    if dele > 0 and ins > 0:
        ratio = ins / max(dele, 1)
        if ratio > 5:
            return "feat"
        if 0.5 <= ratio <= 2:
            return "refactor"
        if ratio < 0.5:
            return "remove"  # mostly deletion
    return "feat"


def classify_commit(subject: str, files_kinds: list[str]) -> str:
    """Commit-Subject + dominant file-kind."""
    if FIX_KEYWORDS.search(subject):
        return "fix"
    if REFACTOR_KEYWORDS.search(subject):
        return "refactor"
    if FEAT_KEYWORDS.search(subject):
        return "feat"
    # Fallback: dominant file kind
    if files_kinds:
        from collections import Counter
        return Counter(files_kinds).most_common(1)[0][0]
    return "feat"


# ──────────────────────────────────────────────────────────────────────────
# Git-Interaktion
# ──────────────────────────────────────────────────────────────────────────


def run_git(args: list[str], repo: Path) -> str:
    """Run git command in repo dir."""
    result = subprocess.run(
        ["git", "-C", str(repo)] + args,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def parse_numstat(output: str) -> list[dict]:
    """Parse `git diff --numstat` output into per-file dicts."""
    files = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ins_str, del_str, path = parts[0], parts[1], parts[2]
        try:
            ins = int(ins_str) if ins_str != "-" else 0
            dele = int(del_str) if del_str != "-" else 0
        except ValueError:
            continue
        files.append({"path": path, "ins": ins, "del": dele})
    return files


def parse_commits(output: str) -> list[dict]:
    """Parse `git log --oneline` output."""
    commits = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha, subject = parts[0], parts[1]
        commits.append({"sha": sha, "subject": subject})
    return commits


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────


def summarize(repo: Path, diff_range: str, top: int | None) -> dict:
    """Build full summary dict."""
    numstat = run_git(["diff", "--numstat", diff_range], repo)
    files = parse_numstat(numstat)

    # Classify each file
    for f in files:
        f["type"] = classify_file(f["path"], f["ins"], f["del"])

    # Aggregate
    total_ins = sum(f["ins"] for f in files)
    total_del = sum(f["del"] for f in files)
    from collections import Counter
    by_type = dict(Counter(f["type"] for f in files))

    # Sort by total LoC change (ins + del), top-N if requested
    files_sorted = sorted(files, key=lambda f: f["ins"] + f["del"], reverse=True)
    if top:
        files_sorted = files_sorted[:top]

    # Commits in range
    try:
        log_output = run_git(["log", "--oneline", "--no-merges", diff_range], repo)
        commits = parse_commits(log_output)
        # Classify commits
        files_kinds = [f["type"] for f in files]
        for c in commits:
            c["type"] = classify_commit(c["subject"], files_kinds)
    except RuntimeError:
        commits = []

    return {
        "range": diff_range,
        "repo": str(repo),
        "total_insertions": total_ins,
        "total_deletions": total_del,
        "files_changed": len(files),
        "by_type": by_type,
        "files": files_sorted,
        "commits": commits,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Strukturierte Code-Diff-Summary für Code-Review-Vorbereitung."
    )
    p.add_argument(
        "range",
        nargs="?",
        default="HEAD~1..HEAD",
        help="Git-Range (default: HEAD~1..HEAD)",
    )
    p.add_argument(
        "--repo",
        default=os.getcwd(),
        help="Repo-Pfad (default: aktuelles dir)",
    )
    p.add_argument(
        "--top",
        type=int,
        default=None,
        help="Nur Top-N grösste Files in Output (default: alle)",
    )
    p.add_argument(
        "--commits-only",
        action="store_true",
        help="Nur Commits-Liste, keine File-Stats (kompakteste Form)",
    )
    args = p.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(json.dumps({"error": f"{repo} is not a git repo"}), file=sys.stderr)
        return 2

    try:
        result = summarize(repo, args.range, args.top)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1

    if args.commits_only:
        print(json.dumps({"range": result["range"], "commits": result["commits"]}, indent=2))
    else:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
