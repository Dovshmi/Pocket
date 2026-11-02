"""Tests for PocketDesk's portable data functions. Run: py -3 test_storage.py"""
from pathlib import Path
import runpy
import tempfile
import unittest

m = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"), run_name="test_import")


class TestStorage(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nested" / "data.json"
            data = m["default_data"]()
            data["notes"][0]["body"] = "Hebrew עברית / Русский / emojis ✏️"
            m["save_data"](path, data)
            self.assertEqual(m["load_data"](path), data)

    def test_normalize_url(self):
        normalize = m["normalize_url"]
        self.assertEqual(normalize("github.com"), "https://github.com")
        self.assertEqual(normalize("https://example.org/a"), "https://example.org/a")
        for invalid in ("", "javascript:alert(1)", "file:///test", "http://", "not a URL"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    normalize(invalid)

    def test_corrupt_file_backup(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.json"
            path.write_text("{bad", encoding="utf-8")
            result = m["load_data"](path)
            self.assertTrue(result["notes"])
            self.assertEqual(len(list(Path(d).glob("data-corrupt-*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
