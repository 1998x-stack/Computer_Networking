"""Idempotent migration of pre-rendered HTML pages away from unsafe scripts.

This only edits existing HTML files; Markdown, Python and PDF files are untouched.
Run with --check in CI to guard against regressions.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

POLYFILL = '<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>'
HIGHLIGHT = (
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/'
    'highlight.js/11.4.0/highlight.min.js"></script>'
)
HIGHLIGHT_DEFER = HIGHLIGHT.replace("<script src=", "<script defer src=")
INLINE_HIGHLIGHT = "<script>hljs.highlightAll();</script>"
MATHJAX_OLD = (
    '<script id="MathJax-script" async src="https://cdn.jsdelivr.net/'
    'npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
)
MATHJAX_NEW = (
    '<script id="MathJax-script" defer src="https://cdn.jsdelivr.net/'
    'npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script>'
)
MATHJAX_AND_MARKDOWN = re.compile(
    r'(?m)^([ \t]*)' + re.escape(MATHJAX_OLD)
    + r'\r?\n[ \t]*<script src="([^"]*markdown\.js)"></script>'
)


def transform_html(content: str) -> str:
    """Rewrite known generated-page script tags, preserving article markup."""
    if POLYFILL not in content:
        if "polyfill.io" in content:
            raise ValueError("Unrecognized polyfill.io reference")
        return content  # index.html and already migrated pages

    for expected in (HIGHLIGHT, INLINE_HIGHLIGHT, MATHJAX_OLD):
        if content.count(expected) != 1:
            raise ValueError(f"Expected exactly one legacy script tag: {expected}")
    if len(MATHJAX_AND_MARKDOWN.findall(content)) != 1:
        raise ValueError("Expected one adjacent MathJax / markdown.js script pair")

    changed = content.replace(POLYFILL, "")
    changed = changed.replace(HIGHLIGHT, HIGHLIGHT_DEFER)
    changed = changed.replace(INLINE_HIGHLIGHT, "")
    changed = MATHJAX_AND_MARKDOWN.sub(
        lambda match: (
            match.group(1) + '<script defer src="' + match.group(2) + '"></script>\n'
            + match.group(1) + MATHJAX_NEW
        ),
        changed,
    )
    if "polyfill.io" in changed or INLINE_HIGHLIGHT in changed:
        raise ValueError("Migration left a legacy script reference")
    return changed


def audit(root: Path, *, check: bool) -> tuple[int, int]:
    """Return number of visited pages and stale pages; raise on malformed HTML."""
    pages = sorted(root.rglob("*.html"))
    if not pages:
        raise ValueError(f"No HTML pages found beneath {root}")

    stale = 0
    for page in pages:
        old = page.read_text(encoding="utf-8")
        new = transform_html(old)
        if new != old:
            stale += 1
            if not check:
                page.write_text(new, encoding="utf-8")
        elif "markdown.js" in old:
            # Refuse silently half-migrated pages.
            if MATHJAX_NEW not in old or HIGHLIGHT_DEFER not in old:
                raise ValueError(f"HTML page is missing required deferred scripts: {page}")
    return len(pages), stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Read only; fail if migration needed")
    args = parser.parse_args()
    total, stale = audit(args.root, check=args.check)
    print(f"HTML pages checked: {total}; {'stale' if args.check else 'updated'}: {stale}")
    return int(args.check and stale > 0)


if __name__ == "__main__":
    raise SystemExit(main())
