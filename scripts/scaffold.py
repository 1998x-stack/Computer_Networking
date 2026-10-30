"""Non-destructive scaffolding for the textbook chapter manifest.

Existing Markdown notes, Python files, and README.md are never overwritten.
This module uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ScaffoldResult:
    """Files that were created, preserved, or found missing."""

    created: tuple[Path, ...]
    preserved: tuple[Path, ...]
    missing: tuple[Path, ...]


def _safe_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("Chapter and section names must be strings")
    normalized = name.replace(" ", "_").replace("/", "_").replace("-", "_")
    if not normalized or normalized in {".", ".."} or "\\" in normalized:
        raise ValueError(f"Invalid chapter or section name: {name!r}")
    return normalized


def build_manifest(
    structure: Mapping[str, Mapping[str, list[str]]],
) -> list[tuple[Path, str]]:
    """Return expected relative file paths and initial file content.

    This reproduces the repository's original path normalization and numbering.
    Existing files are intentionally not read or modified here.
    """
    manifest: list[tuple[Path, str]] = []
    readme = [
        "# Computer Network",
        "",
        "这是一个关于Computer Network的目录结构。",
        "",
    ]

    for chapter, sections in structure.items():
        chapter_dir = _safe_name(chapter)
        readme.extend((f"# {chapter}", ""))

        for section, items in sections.items():
            if not isinstance(items, list) or not all(
                isinstance(item, str) for item in items
            ):
                raise TypeError(f"Expected a list of titles in {chapter}/{section}")

            directory = Path(chapter_dir) / _safe_name(section)
            readme.extend((f"## {chapter}/{section}", ""))
            titles = (
                [f"{index:02d}_{item}" for index, item in enumerate(items)]
                if items
                else [section]
            )

            for title in titles:
                stem = _safe_name(title)
                initial_content = (
                    f"# {title}\n\n"
                    f'"""\nLecture: {chapter}/{section}\n'
                    f'Content: {title}\n"""\n\n'
                )
                for suffix in (".py", ".md"):
                    relative_path = directory / (stem + suffix)
                    manifest.append((relative_path, initial_content))
                    readme.append(f"- [{title}](./{relative_path.as_posix()})")
            readme.append("")

    manifest.append((Path("README.md"), "\n".join(readme).rstrip() + "\n"))
    paths = [path for path, _ in manifest]
    if len(paths) != len(set(paths)):
        raise ValueError("The chapter structure generates duplicate paths")
    return manifest


def scaffold(
    root: Path,
    structure: Mapping[str, Mapping[str, list[str]]],
    *,
    dry_run: bool = False,
    check: bool = False,
) -> ScaffoldResult:
    """Generate missing files only, or preview/check without modifying disk.

    dry_run: list missing files without writing anything.
    check: same read-only behavior; callers should exit nonzero if missing.
    """
    if dry_run and check:
        raise ValueError("Choose either dry_run or check")
    root = Path(root)
    created: list[Path] = []
    preserved: list[Path] = []
    missing: list[Path] = []

    for relative, content in build_manifest(structure):
        target = root / relative
        if target.is_dir():
            raise IsADirectoryError(f"Expected a file, found a directory: {target}")
        if target.exists() or target.is_symlink():
            preserved.append(relative)
            continue
        if dry_run or check:
            missing.append(relative)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("x", encoding="utf-8") as handle:
                handle.write(content)
        except FileExistsError:
            # Another process created the file after the existence check.
            preserved.append(relative)
        else:
            created.append(relative)

    return ScaffoldResult(tuple(created), tuple(preserved), tuple(missing))
