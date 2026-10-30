"""P0-M3: fixtures for deterministic documentation builds."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_docs import build, expected_pages, markdown_body, validate_pages


class DocsBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        topic = self.root / "1_Introduction" / "1.1_Internet"
        topic.mkdir(parents=True)
        (topic / "00_1.1.1_Basics.md").write_text(
            '# 00_1.1.1_Basics\n\n"""\nLecture: 1/1.1\nContent: Basics\n"""\n\n'
            '## 演示\n\nSome inline math $L/R$ and a table:\n\n'
            '| A | B |\n| --- | --- |\n| 1 | 2 |\n\n'
            '~~~python\nprint("hello")\n~~~\n'
            '\n<script>alert("untrusted")</script>\n',
            encoding="utf-8",
        )
        (topic / "00_1.1.1_Basics.py").write_text(
            '# Basic example\nprint("hello")\n',
            encoding="utf-8",
        )
        (self.root / "README.md").write_text(
            '# Index\n\n[Read it](./1_Introduction/1.1_Internet/00_1.1.1_Basics.md)\n',
            encoding="utf-8",
        )
        for filename in ("style.css", "markdown.css", "markdown.js"):
            (self.root / filename).write_text("/* fixture */", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_expected_pages_have_readme_chapter_and_index(self):
        pages = expected_pages(self.root)
        self.assertEqual(len(pages), 3)
        self.assertIn(self.root / "index.html", pages)
        self.assertIn(self.root / "README.html", pages)
        chapter = next(v for k, v in pages.items() if k.name == "00_1.1.1_Basics.html")
        self.assertIn('<table>', chapter)
        self.assertIn('class="math"', chapter)
        self.assertIn('Python 文件', chapter)
        self.assertIn('00_1.1.1_Basics.html', pages[self.root / "README.html"])
        self.assertNotIn('00_1.1.1_Basics.md', pages[self.root / "README.html"])

    def test_raw_html_is_escaped_by_renderer(self):
        rendered = markdown_body('<script>alert("bad")</script>')
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_check_mode_does_not_modify_files(self):
        count, stale = build(self.root, write=False)
        self.assertEqual((count, stale), (3, 3))
        self.assertFalse((self.root / "index.html").exists())

    def test_write_is_deterministic(self):
        self.assertEqual(build(self.root, write=True), (3, 3))
        first = (self.root / "index.html").read_bytes()
        self.assertEqual(build(self.root, write=False), (3, 0))
        self.assertEqual(build(self.root, write=True), (3, 0))
        self.assertEqual(first, (self.root / "index.html").read_bytes())

    def test_broken_internal_link_is_rejected_without_writes(self):
        (self.root / "README.md").write_text(
            "[missing](./1_Introduction/1.1_Internet/not-found.md)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "Broken local href"):
            build(self.root, write=True)
        self.assertFalse((self.root / "index.html").exists())

    def test_unapproved_external_script_is_rejected(self):
        pages = expected_pages(self.root)
        index = self.root / "index.html"
        pages[index] += '<script src="https://not-approved.example/script.js"></script>'
        errors = validate_pages(self.root, pages)
        self.assertTrue(any("Disallowed remote script" in e for e in errors))

    def test_missing_companion_is_rejected(self):
        next(self.root.glob("1_*/**/*.py")).unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.root, write=False)


if __name__ == "__main__":
    unittest.main()
