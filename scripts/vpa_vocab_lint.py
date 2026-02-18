#!/usr/bin/env python3
"""
VPA vocabulary linter — enforces the blacklist / exceptions contract.

Scans *.py, *.md, *.yaml files for blacklisted terms and reports violations.
Files listed in VPA_VOCAB_EXCEPTIONS.txt are skipped.

Exit code:
    0  — no violations
    1  — violations found (CI gate fail)

Usage:
    python scripts/vpa_vocab_lint.py                  # scan from repo root
    python scripts/vpa_vocab_lint.py --root /some/path
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".venv", ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}
SCAN_EXTENSIONS = {".py", ".md", ".yaml", ".yml"}


def _load_lines(path: Path) -> list[str]:
    """Load non-empty, stripped lines from a text file."""
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]


def _load_blacklist(root: Path) -> list[str]:
    return _load_lines(root / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt")


def _load_exception_filenames(root: Path) -> set[str]:
    """Return set of lowercased basenames that are exempt from scanning."""
    lines = _load_lines(root / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt")
    return {ln.lower() for ln in lines if "." in ln}


def _build_patterns(terms: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """Compile each blacklist term into a word-boundary regex."""
    patterns = []
    for term in terms:
        escaped = re.escape(term)
        pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        patterns.append((term, pattern))
    return patterns


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def scan(root: Path) -> list[tuple[str, int, str, str]]:
    """Scan the repo and return a list of (filepath, line_no, term, line_text) violations."""
    blacklist = _load_blacklist(root)
    if not blacklist:
        return []

    exceptions = _load_exception_filenames(root)
    patterns = _build_patterns(blacklist)
    violations: list[tuple[str, int, str, str]] = []

    for ext in SCAN_EXTENSIONS:
        for filepath in root.rglob(f"*{ext}"):
            if _should_skip(filepath):
                continue
            if filepath.name.lower() in exceptions:
                continue
            try:
                text = filepath.read_text(errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for term, pattern in patterns:
                    if pattern.search(line):
                        rel = filepath.relative_to(root)
                        violations.append((str(rel), line_no, term, line.strip()))

    violations.sort()
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VPA vocabulary linter")
    parser.add_argument("--root", type=Path, default=None, help="Repo root (default: auto-detect)")
    args = parser.parse_args(argv)

    root = args.root
    if root is None:
        root = Path(__file__).resolve().parent.parent
    root = root.resolve()

    violations = scan(root)

    if not violations:
        print("vpa-vocab-lint: PASS (0 violations)")
        return 0

    print(f"vpa-vocab-lint: FAIL ({len(violations)} violation(s))\n")
    for filepath, line_no, term, text in violations:
        print(f"  {filepath}:{line_no}  [{term}]")
        print(f"    {text[:120]}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
