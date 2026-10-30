"""Regression tests for the non-destructive chapter scaffold."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from main import main, structure
from scripts.scaffold import build_manifest, scaffold


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_manifest_has_all_chapters_and_matching_links(self):
        manifest = build_manifest(structure)
        self.assertEqual(len(manifest), 425)  # 212 chapters * 2 + README
        paths = {path for path, _ in manifest}
        self.assertIn(Path("README.md"), paths)
        self.assertIn(
            Path(
                "1_Computer_Networks_and_the_Internet"
                "/1.1_What_is_the_Internet"
                "/00_1.1.1_A_Nuts_and_Bolts_Description.md"
            ),
            paths,
        )
        readme = next(content for path, content in manifest if path.name == "README.md")
        self.assertEqual(readme.count("](./"), 424)

    def test_dry_run_does_not_create_anything(self):
        report = scaffold(self.root, structure, dry_run=True)
        self.assertEqual(len(report.missing), 425)
        self.assertFalse(list(self.root.iterdir()))

    def test_generation_and_second_run_are_idempotent(self):
        first = scaffold(self.root, structure)
        self.assertEqual(len(first.created), 425)
        self.assertEqual(len(first.preserved), 0)
        second = scaffold(self.root, structure)
        self.assertEqual(len(second.created), 0)
        self.assertEqual(len(second.preserved), 425)
        self.assertFalse(second.missing)

    def test_modified_notes_and_readme_are_never_rewritten(self):
        scaffold(self.root, structure)
        note = self.root / (
            "1_Computer_Networks_and_the_Internet"
            "/1.1_What_is_the_Internet"
            "/00_1.1.1_A_Nuts_and_Bolts_Description.md"
        )
        readme = self.root / "README.md"
        note.write_text("# Personal research notes\n", encoding="utf-8")
        readme.write_text("# Custom homepage\n", encoding="utf-8")
        report = scaffold(self.root, structure)
        self.assertFalse(report.created)
        self.assertEqual(note.read_text(encoding="utf-8"), "# Personal research notes\n")
        self.assertEqual(readme.read_text(encoding="utf-8"), "# Custom homepage\n")

    def test_existing_readme_is_preserved_during_initial_creation(self):
        (self.root / "README.md").write_text("Important custom content\n", encoding="utf-8")
        report = scaffold(self.root, structure)
        self.assertEqual(len(report.created), 424)
        self.assertEqual(len(report.preserved), 1)
        self.assertEqual(
            (self.root / "README.md").read_text(encoding="utf-8"),
            "Important custom content\n",
        )

    def test_check_reports_missing_files_and_succeeds_after_generation(self):
        result = scaffold(self.root, structure, check=True)
        self.assertEqual(len(result.missing), 425)
        scaffold(self.root, structure)
        result = scaffold(self.root, structure, check=True)
        self.assertFalse(result.missing)

    def test_cli_dry_run_check_and_write(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root), "--dry-run"]), 0)
            self.assertEqual(main(["--root", str(self.root), "--check"]), 1)
            self.assertEqual(main(["--root", str(self.root)]), 0)
            self.assertEqual(main(["--root", str(self.root), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
