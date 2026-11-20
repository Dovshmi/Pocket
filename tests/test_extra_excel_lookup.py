"""Regression coverage for Pocket Extra's strictly read-only Excel search."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from pocket.extra_excel_lookup import (
    display_value, match_quality, normalize_group_code, search_workbook,
)


class ExtraExcelLookupTests(unittest.TestCase):
    def test_group_codes_are_separator_independent(self):
        for stored in ("8826004", "88-26004", "88 26004", "88–26004", "88—26004"):
            self.assertEqual(normalize_group_code(stored), "8826004")
            self.assertEqual(match_quality("8826004", stored), 2)
            self.assertEqual(match_quality("88-26004", stored), 2)
        self.assertIsNone(normalize_group_code("192.168.1.1"))
        self.assertEqual(match_quality("acme", "ACME Branch"), 1)
        self.assertEqual(display_value(88.0), "88")

    def test_search_every_sheet_and_preserve_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference.xlsx"
            wb = Workbook()
            sheet = wb.active
            sheet.title = "FG-1"
            sheet.append(["Customer", "Group code", "VRF", "VDOM", "IP address"])
            sheet.append(["Sample Customer", "88-26004", "example-vrf", "VDOM-A", "10.1.2.0/30"])
            sheet.append(["Different Customer", "88-29001", "other-vrf", "VDOM-B", "10.1.3.0/30"])
            second = wb.create_sheet("FG-2")
            second.append(["שם לקוח", "קוד קבוצה", "VLAN"])
            second.append(["לקוח בדיקה", 8826004, 408])
            wb.save(path)
            wb.close()
            before = hashlib.sha256(path.read_bytes()).digest()

            hits, capped = search_workbook(path, "8826004")
            self.assertFalse(capped)
            self.assertEqual(len(hits), 2)
            self.assertEqual([(hit.sheet, hit.row) for hit in hits],
                             [("FG-1", 2), ("FG-2", 2)])
            self.assertTrue(all(hit.exact for hit in hits))
            self.assertIn(("VRF (C)", "example-vrf"), hits[0].fields)
            self.assertIn("Group code (B)", hits[0].matched_columns)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

            # Partial text, IP prefix and VRF searches also work.
            self.assertEqual(len(search_workbook(path, "sample customer")[0]), 1)
            self.assertEqual(len(search_workbook(path, "10.1.2")[0]), 1)
            self.assertEqual(len(search_workbook(path, "example-vrf")[0]), 1)
            self.assertEqual(len(search_workbook(path, "לקוח בדיקה")[0]), 1)

    def test_bounded_search_and_bad_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "large.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.append(["Customer", "Group code", "VRF"])
            for index in range(10):
                ws.append(["Test customer", f"88-{26000 + index}", "testing"])
            wb.save(path)
            wb.close()

            hits, capped = search_workbook(path, "testing", limit=3)
            self.assertEqual(len(hits), 3)
            self.assertTrue(capped)
            hits, capped = search_workbook(path, "testing", cancelled=lambda: True)
            self.assertEqual(hits, [])
            self.assertFalse(capped)
            with self.assertRaises(ValueError):
                search_workbook(path.with_suffix(".csv"), "testing")
            with self.assertRaises(FileNotFoundError):
                search_workbook(path.with_name("missing.xlsx"), "testing")


if __name__ == "__main__":
    unittest.main()
