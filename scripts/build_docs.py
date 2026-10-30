"""Build and validate the static site from Markdown and optional Python examples.

Source of truth: 212 chapter Markdown files plus root README.md. This command
never modifies Markdown, Python or PDF. Only --write changes generated HTML.

Install with: python -m pip install -r requirements-docs.txt
"""

from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import mistune

MARKDOWN = mistune.create_markdown(
    renderer=mistune.HTMLRenderer(escape=True),
    plugins=["table", "strikethrough", "url", "math"],
)
DOCSTRING = re.compile(r'\A(#[^\n]*\n\n)"""\n(.*?)\n"""\n', re.DOTALL)
MD_HREF = re.compile(r'(\bhref=")([^"]+\.md)((?:\?[^"#]*)?(?:#[^"]*)?)(")')
ALLOWED_SCRIPT_HOSTS = {"cdnjs.cloudflare.com", "cdn.jsdelivr.net"}


def page_template(body: str, title: str, prefix: str) -> str:
    """Render a chapter or README page with the shared, secured reader assets."""
    return (
        '<!doctype html>\n<html lang="zh-CN">\n<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'  <title>{html.escape(title)}</title>\n'
        '  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/'
        'highlight.js/11.4.0/styles/default.min.css">\n'
        '  <script defer src="https://cdnjs.cloudflare.com/ajax/libs/'
        'highlight.js/11.4.0/highlight.min.js"></script>\n'
        '  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=STIX+Two+Math&display=swap">\n'
        f'  <link rel="stylesheet" href="{prefix}markdown.css">\n'
        f'  <script defer src="{prefix}markdown.js"></script>\n'
        '  <script id="MathJax-script" defer src="https://cdn.jsdelivr.net/'
        'npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script>\n'
        '</head>\n<body>\n'
        f'  <div class="container">\n{body}\n  </div>\n'
        '</body>\n</html>\n'
    )


def markdown_body(source: str) -> str:
    """Render Markdown without permitting embedded raw HTML execution."""
    source = DOCSTRING.sub(
        lambda match: match.group(1) + "~~~text\n" + match.group(2) + "\n~~~\n",
        source,
        count=1,
    )
    markup = MARKDOWN(source)
    # README navigation points at rendered chapter pages instead of raw .md.
    return MD_HREF.sub(
        lambda match: match.group(1) + match.group(2)[:-3] + ".html"
        + match.group(3) + match.group(4),
        markup,
    ).rstrip()


def get_chapters(root: Path) -> list[Path]:
    paths = sorted(
        p for p in root.glob("[1-9]_*/**/*.md")
        if p.is_file()
    )
    if not paths:
        raise ValueError("No chapter Markdown files were found")
    return paths


def build_index(chapters: list[Path], root: Path) -> str:
    """Generate a stable, simple index from the actual chapter content tree."""
    groups: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for path in chapters:
        rel = path.relative_to(root)
        if len(rel.parts) != 3:
            raise ValueError(f"Unexpected chapter nesting: {rel}")
        groups[rel.parts[0]][rel.parts[1]].append(rel)

    lines = [
        '<!doctype html>', '<html lang="zh-CN">', '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>Computer Networking — 章节目录</title>',
        '<link rel="stylesheet" href="style.css">',
        '</head>', '<body>', '<main class="container">',
        '<h1>Computer Networking — 章节目录</h1>',
        '<p><a href="README.html">查看完整课程导航</a></p>',
    ]
    for chapter, sections in sorted(groups.items()):
        lines.append(f'<section class="tree-container"><h2>{html.escape(chapter.replace("_", " "))}</h2>')
        for section, documents in sorted(sections.items()):
            lines.append(f'<h3>{html.escape(section.replace("_", " "))}</h3><ul>')
            for document in sorted(documents):
                title = re.sub(r"^\d\d_", "", document.stem).replace("_", " ")
                href = html.escape(document.with_suffix(".html").as_posix(), quote=True)
                lines.append(f'<li class="link-item"><a href="{href}">{html.escape(title)}</a></li>')
            lines.append('</ul>')
        lines.append('</section>')
    lines.extend(['</main>', '</body>', '</html>', ''])
    return "\n".join(lines)


def expected_pages(root: Path) -> dict[Path, str]:
    chapters = get_chapters(root)
    expected: dict[Path, str] = {}
    readme = root / "README.md"
    if not readme.is_file():
        raise FileNotFoundError(readme)

    expected[root / "README.html"] = page_template(
        markdown_body(readme.read_text(encoding="utf-8")),
        "Computer Networking — README",
        "",
    )
    for source in chapters:
        python_file = source.with_suffix(".py")
        if not python_file.is_file():
            raise FileNotFoundError(f"Missing Python companion: {python_file}")
        markdown = markdown_body(source.read_text(encoding="utf-8"))
        sample = html.escape(python_file.read_text(encoding="utf-8"))
        body = markdown + '\n<h3>Python 文件</h3>\n<pre><code>' + sample + '</code></pre>'
        expected[source.with_suffix(".html")] = page_template(
            body, re.sub(r"^\d\d_", "", source.stem).replace("_", " "),
            "../../",
        )
    expected[root / "index.html"] = build_index(chapters, root)
    return expected


class LocalLinkChecker(HTMLParser):
    """Check local href/src targets and block unsafe external script origins."""

    def __init__(self, root: Path, page: Path, generated: set[Path]):
        super().__init__(convert_charrefs=True)
        self.root = root.resolve()
        self.page = page
        self.generated = generated
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        for attribute in ("href", "src"):
            if attribute not in attributes or not attributes[attribute]:
                continue
            value = attributes[attribute] or ""
            if value.startswith("#"):
                continue
            split = urlsplit(value)
            if split.scheme or split.netloc:
                if tag == "script":
                    if split.scheme != "https" or split.hostname not in ALLOWED_SCRIPT_HOSTS:
                        self.errors.append(f"Disallowed remote script: {value}")
                elif tag in {"link", "img"} and split.scheme not in {"https", "data"}:
                    self.errors.append(f"Insecure remote resource: {value}")
                continue
            local = (self.page.parent / unquote(split.path)).resolve()
            if not local.is_relative_to(self.root):
                self.errors.append(f"Path escapes repository: {value}")
            elif local not in self.generated and not local.is_file():
                self.errors.append(f"Broken local {attribute}: {value}")


def validate_pages(root: Path, pages: dict[Path, str]) -> list[str]:
    files = {path.resolve() for path in pages}
    errors: list[str] = []
    for path, content in pages.items():
        checker = LocalLinkChecker(root, path, files)
        checker.feed(content)
        errors.extend(f"{path.relative_to(root)}: {error}" for error in checker.errors)
    return errors


def build(root: Path, *, write: bool) -> tuple[int, int]:
    root = root.resolve()
    pages = expected_pages(root)
    problems = validate_pages(root, pages)
    if problems:
        raise ValueError("Site validation failed:\n" + "\n".join(problems[:25]))
    changed = 0
    for target, content in pages.items():
        if target.is_symlink():
            raise ValueError(f"Refusing to overwrite symlink: {target}")
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            continue
        changed += 1
        if write:
            target.write_text(content, encoding="utf-8")
    return len(pages), changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true", help="Update generated HTML pages")
    modes.add_argument("--check", action="store_true", help="Read-only; fail on stale HTML")
    args = parser.parse_args()
    count, stale = build(args.root, write=args.write)
    print(f"Generated HTML pages: {count}; {'updated' if args.write else 'stale'}: {stale}")
    return 1 if not args.write and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
