"""Ensure all public release surfaces agree before a tag is published."""
from pathlib import Path
import unittest

from pocket import app_info

ROOT = Path(__file__).resolve().parents[1]


class ReleaseVersionTests(unittest.TestCase):
    def test_development_settings_version_is_v143(self):
        # The development application version is independent of published release assets.
        self.assertEqual(app_info.VERSION, "1.43.0")
        self.assertEqual(app_info.version_label(), "v1.43")
        self.assertEqual(app_info.AUTHOR_CREDIT, "By. Rony Shmidov")
        settings = (ROOT / "pocket" / "settings_ui.py").read_text(encoding="utf-8")
        self.assertIn('"Version " + app_info.version_label()', settings)

    def test_previous_stable_release_workflow_is_preserved(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "release-v1.39.8.yml").read_text(encoding="utf-8")
        self.assertIn("POCKET_RELEASE_VERSION: v1.39.8", workflow)
        self.assertIn("[release v1.39.8]", workflow)
        self.assertIn("softprops/action-gh-release@v2", workflow)
        self.assertIn("tag_name: v1.39.8", workflow)
        self.assertIn("target_commitish: ${{ github.sha }}", workflow)
        self.assertIn("make_latest: true", workflow)
        self.assertIn("test_packaged_release.py" not in workflow and
                      "check_packaged_release.py" in workflow, (True,))
        self.assertIn("Pocket-Portable-v1.39.8.zip", workflow)
        self.assertIn("Pocket-v1.39.8.exe", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn("docs/releases/v1.39.8.md", workflow)
        self.assertIn("smoke_quick_slots_selection.py", workflow)
        self.assertIn("probe_quick_slots_win32.py", workflow)
        self.assertIn("fail_on_unmatched_files: true", workflow)

    def test_packager_and_dev_ci_build_the_same_zip_version(self):
        packager = (ROOT / "package_portable.py").read_text(encoding="utf-8")
        smoke = (ROOT / ".github" / "workflows" /
                 "mini-checks.yml").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("POCKET_RELEASE_VERSION", "v1.43.0")',
                      packager)
        self.assertIn("Pocket-Portable-v1.43.0.zip", smoke)
        self.assertIn("--version v1.43.0", smoke)

    def test_v1399_release_workflow_requires_explicit_authorization(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "release-v1.39.9.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("confirm_version:", workflow)
        self.assertNotIn("  push:\n", workflow)
        self.assertIn("github.repository == 'Dovshmi/Pocket'", workflow)
        self.assertIn("app_info.VERSION == '1.39.9'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("inputs.confirm_version == 'v1.39.9'", workflow)
        self.assertIn("POCKET_RELEASE_VERSION: v1.39.9", workflow)
        self.assertIn("tag_name: v1.39.9", workflow)
        self.assertIn("softprops/action-gh-release@v2", workflow)
        self.assertIn("make_latest: true", workflow)
        self.assertIn("smoke_notes_reminders_v1399.py", workflow)
        self.assertIn("Pocket-Portable-v1.39.9.zip", workflow)
        self.assertIn("Pocket-v1.39.9.exe", workflow)
        self.assertIn("docs/releases/v1.39.9.md", workflow)
        release_body = (ROOT / "docs" / "releases" / "v1.39.9.md").read_text(encoding="utf-8")
        self.assertIn("Pocket v1.39.9", release_body)
        self.assertIn("Clear", release_body)

    def test_v140_official_windows_release_workflow(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "release-v1.40.0.yml").read_text(encoding="utf-8")
        self.assertIn("github.repository == 'Dovshmi/Pocket'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("[release v1.40.0]", workflow)
        self.assertIn("inputs.confirm_version == 'v1.40.0'", workflow)
        self.assertIn("app_info.VERSION == '1.40.0'", workflow)
        self.assertIn("POCKET_RELEASE_VERSION: v1.40.0", workflow)
        self.assertIn("smoke_menu_order_v140.py", workflow)
        self.assertIn("smoke_extra_arrows_v140.py", workflow)
        self.assertIn("smoke_notes_reminders_v1399.py", workflow)
        self.assertIn("--collect-all openpyxl", workflow)
        self.assertIn("--collect-all xlrd", workflow)
        self.assertIn("--hidden-import win32com.client", workflow)
        self.assertIn("check_packaged_release.py --version v1.40.0", workflow)
        self.assertIn("softprops/action-gh-release@v2", workflow)
        self.assertIn("tag_name: v1.40.0", workflow)
        self.assertIn("target_commitish: ${{ github.sha }}", workflow)
        self.assertIn("make_latest: true", workflow)
        self.assertIn("fail_on_unmatched_files: true", workflow)
        self.assertIn("Pocket-Portable-v1.40.0.zip", workflow)
        self.assertIn("Pocket-v1.40.0.exe", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        release_notes = (ROOT / "docs" / "releases" /
                         "v1.40.0.md").read_text(encoding="utf-8")
        self.assertIn("Outlook", release_notes)
        self.assertIn("not encrypted", release_notes)
        self.assertIn("Excel", release_notes)

    def test_v142_release_workflow(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "release-v1.42.0.yml").read_text(encoding="utf-8")
        for marker in ("[release v1.42.0]", "inputs.confirm_version == 'v1.42.0'",
                       "app_info.VERSION == '1.42.0'", "github.ref == 'refs/heads/main'",
                       "smoke_adaptive_v141.py", "smoke_native_inputs.py",
                       "check_packaged_release.py --version v1.42.0",
                       "tag_name: v1.42.0", "make_latest: true",
                       "Pocket-Portable-v1.42.0.zip", "Pocket-v1.42.0.exe",
                       "SHA256SUMS.txt", "fail_on_unmatched_files: true"):
            self.assertIn(marker, workflow)
        notes = (ROOT / "docs" / "releases" / "v1.42.0.md").read_text(encoding="utf-8")
        for marker in ("Ctrl+K", "not encrypted", "v1.41", "MAC Vendor"):
            self.assertIn(marker, notes)

    def test_readme_and_release_notes_point_to_new_assets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        self.assertIn("/releases/download/v1.42.0/Pocket-Portable-v1.42.0.zip",
                      readme)
        self.assertIn("/releases/download/v1.42.0/Pocket-v1.42.0.exe", readme)
        self.assertIn("# Pocket v1.39.8", notes)
        self.assertIn("Database", notes)
        self.assertIn("Clipboard", notes)
        self.assertIn("/releases/download/v1.42.0/Pocket-Portable-v1.42.0.zip", readme)
        self.assertIn("/releases/download/v1.42.0/Pocket-v1.42.0.exe", readme)
        self.assertIn("/releases/download/v1.42.0/SHA256SUMS.txt", readme)
        self.assertIn("Quick Slots", readme)
        self.assertIn("Backup & Restore", readme)
        release_body = (ROOT / "docs" / "releases" / "v1.39.8.md").read_text(encoding="utf-8")
        self.assertIn("Pocket v1.39.8", release_body)
        self.assertIn("SHA256SUMS.txt", release_body)


if __name__ == "__main__":
    unittest.main()
