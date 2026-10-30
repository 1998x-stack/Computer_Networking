"""Tests for the security migration and its read-only audit mode."""

import tempfile
import unittest
from pathlib import Path

from scripts.migrate_html_security import (
    HIGHLIGHT,
    HIGHLIGHT_DEFER,
    INLINE_HIGHLIGHT,
    MATHJAX_NEW,
    MATHJAX_OLD,
    POLYFILL,
    audit,
    transform_html,
)


def sample_html():
    return (
        '<!doctype html><html><head>\n'
        f'  {HIGHLIGHT}\n'
        f'  {INLINE_HIGHLIGHT}\n'
        f'  {POLYFILL}\n'
        f'  {MATHJAX_OLD}\n'
        '  <script src="../../markdown.js"></script>\n'
        '</head><body><main>important content</main></body></html>\n'
    )


class MigrationTests(unittest.TestCase):
    def test_preserves_content_and_normalizes_script_order(self):
        migrated = transform_html(sample_html())
        self.assertNotIn("polyfill.io", migrated)
        self.assertNotIn(INLINE_HIGHLIGHT, migrated)
        self.assertIn(HIGHLIGHT_DEFER, migrated)
        self.assertIn(MATHJAX_NEW, migrated)
        self.assertIn("important content", migrated)
        self.assertLess(
            migrated.index('<script defer src="../../markdown.js">'),
            migrated.index(MATHJAX_NEW),
        )
        self.assertEqual(transform_html(migrated), migrated)

    def test_unrecognized_polyfill_is_rejected(self):
        with self.assertRaises(ValueError):
            transform_html('<script src="https://polyfill.io/another.js"></script>')

    def test_check_is_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lesson.html"
            original = sample_html()
            p.write_text(original, encoding="utf-8")
            total, stale = audit(Path(d), check=True)
            self.assertEqual((total, stale), (1, 1))
            self.assertEqual(p.read_text(encoding="utf-8"), original)
            self.assertEqual(audit(Path(d), check=False), (1, 1))
            self.assertEqual(audit(Path(d), check=True), (1, 0))

    def test_real_repository_html_is_clean(self):
        root = Path(__file__).resolve().parents[1]
        total, stale = audit(root, check=True)
        self.assertGreaterEqual(total, 214)
        self.assertEqual(stale, 0)


if __name__ == "__main__":
    unittest.main()
