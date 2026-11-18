"""Ensure all public release surfaces agree before a tag is published."""
from pathlib import Path
import unittest

from pocket import app_info

ROOT = Path(__file__).resolve().parents[1]


class ReleaseVersionTests(unittest.TestCase):
    def test_stable_version_is_v1394(self):
        self.assertEqual(app_info.VERSION, "1.39.4")
        self.assertEqual(app_info.version_label(), "v1.39.4")
        self.assertEqual(app_info.AUTHOR_CREDIT, "By. Rony Shmidov")

    def test_release_workflow_has_new_tag_and_safe_build_gates(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "release-v1.39.4.yml").read_text(encoding="utf-8")
        self.assertIn("POCKET_RELEASE_VERSION: v1.39.4", workflow)
        self.assertIn("[release v1.39.4]", workflow)
        self.assertIn("softprops/action-gh-release@v2", workflow)
        self.assertIn("tag_name: v1.39.4", workflow)
        self.assertIn("target_commitish: ${{ github.sha }}", workflow)
        self.assertIn("make_latest: true", workflow)
        self.assertIn("test_packaged_release.py" not in workflow and
                      "check_packaged_release.py" in workflow, (True,))
        self.assertIn("Pocket-Portable-v1.39.4.zip", workflow)
        self.assertIn("Pocket-v1.39.4.exe", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn("docs/releases/v1.39.4.md", workflow)
        self.assertIn("smoke_quick_slots_selection.py", workflow)
        self.assertIn("probe_quick_slots_win32.py", workflow)
        self.assertIn("fail_on_unmatched_files: true", workflow)

    def test_packager_and_dev_ci_build_the_same_zip_version(self):
        packager = (ROOT / "package_portable.py").read_text(encoding="utf-8")
        smoke = (ROOT / ".github" / "workflows" /
                 "mini-checks.yml").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("POCKET_RELEASE_VERSION", "v1.39.4")',
                      packager)
        self.assertIn("Pocket-Portable-v1.39.4.zip", smoke)
        self.assertIn("--version v1.39.4", smoke)

    def test_readme_and_release_notes_point_to_new_assets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertIn("/releases/download/v1.39.4/Pocket-Portable-v1.39.4.zip",
                      readme)
        self.assertIn("/releases/download/v1.39.4/Pocket-v1.39.4.exe", readme)
        self.assertIn("# Pocket v1.39.4", notes)
        self.assertIn("Database", notes)
        self.assertIn("Clipboard", notes)
        self.assertIn("/releases/download/v1.39.4/Pocket-Portable-v1.39.4.zip", readme)
        self.assertIn("/releases/download/v1.39.4/Pocket-v1.39.4.exe", readme)
        self.assertIn("/releases/download/v1.39.4/SHA256SUMS.txt", readme)
        self.assertIn("Quick Slots", readme)
        self.assertIn("Backup & Restore", readme)
        release_body = (ROOT / "docs" / "releases" / "v1.39.4.md").read_text(encoding="utf-8")
        self.assertIn("Pocket v1.39.4", release_body)
        self.assertIn("SHA256SUMS.txt", release_body)


if __name__ == "__main__":
    unittest.main()
