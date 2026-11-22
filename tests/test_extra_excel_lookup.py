"""Regression coverage for Pocket Extra's strictly read-only Excel search."""
from __future__ import annotations

import hashlib
import sys
import types
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from openpyxl import Workbook

from pocket.extra_excel_com import _as_matrix, _matches_file
from pocket.extra_excel_lookup import (
    display_value, match_quality, normalize_group_code, search_workbook,
)


class ExtraExcelLookupTests(unittest.TestCase):
    def test_group_codes_are_separator_independent(self):
        for stored in ("8826004", "88-26004", "88 26004", "88–26004", "88—26004",
                       "88−26004", "88/26004", "88.26004", "88_26004"):
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

    def test_protected_xlsx_falls_back_to_open_excel_without_file_writes(self):
        """A non-ZIP .xlsx must use a read-only Office session, never export data."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "protected.xlsx"
            path.write_bytes(b"encrypted OLE workbook, not a zip archive")
            before = hashlib.sha256(path.read_bytes()).digest()

            def already_open_workbook(_path, **kwargs):
                self.assertEqual(str(_path), str(path))
                yield "Protected FG", iter([
                    (1, ("Customer", "Group code", "VDOM")),
                    (2, ("Example only", "88-26004", "demo-vdom")),
                ])

            with patch("pocket.extra_excel_com.iter_open_excel_sheets",
                       side_effect=already_open_workbook) as office:
                matches, capped = search_workbook(path, "8826004")
            self.assertFalse(capped)
            self.assertEqual(len(matches), 1)
            self.assertEqual((matches[0].sheet, matches[0].row), ("Protected FG", 2))
            self.assertTrue(matches[0].exact)
            self.assertEqual(office.call_count, 1)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_native_excel_matrix_and_exact_path_matching(self):
        self.assertEqual(_as_matrix(42, 1, 1), ((42,),))
        self.assertEqual(_as_matrix((42, 43), 1, 2), ((42, 43),))
        self.assertEqual(_as_matrix(((42,), (43,)), 2, 1), ((42,), (43,)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference.xlsx"
            path.write_bytes(b"test")
            self.assertTrue(_matches_file(path, str(path)))
            self.assertFalse(_matches_file(path, str(path.with_name("other.xlsx"))))

    def test_excel_com_automatically_opens_read_only_and_closes_own_instance(self):
        """Test the Windows COM call contract without Excel or private files."""
        from pocket import extra_excel_com as bridge

        activity = []

        class FakeSheet:
            Name = "Office protected sheet"

            def __init__(self):
                self.UsedRange = types.SimpleNamespace(
                    Row=1, Column=1, Rows=types.SimpleNamespace(Count=2),
                    Columns=types.SimpleNamespace(Count=2))

            def Cells(self, row, col):
                return (row, col)

            def Range(self, first, last):
                return types.SimpleNamespace(
                    Value2=(("Customer", "Group code"), ("Example", "88-26004")))

        class FakeWorkbook:
            Worksheets = [FakeSheet()]

            def Close(self, **kwargs):
                activity.append(("close", kwargs))

        class FakeWorkbooks:
            def __iter__(self):
                return iter(())

            def Open(self, **kwargs):
                activity.append(("open", kwargs))
                return FakeWorkbook()

        class FakeExcel:
            def __init__(self):
                self.Workbooks = FakeWorkbooks()
                self.Visible = True
                self.DisplayAlerts = True
                self.EnableEvents = True
                self.AutomationSecurity = 1
                self.AskToUpdateLinks = True

            def Quit(self):
                activity.append(("quit",))

        instance = FakeExcel()
        fake_client = types.ModuleType("win32com.client")
        def not_open(_prog_id):
            raise RuntimeError("Excel not already running")
        fake_client.GetActiveObject = not_open
        fake_client.DispatchEx = lambda _prog_id: instance
        fake_win32com = types.ModuleType("win32com")
        fake_win32com.__path__ = []
        fake_win32com.client = fake_client
        fake_pythoncom = types.ModuleType("pythoncom")
        fake_pythoncom.CoInitialize = lambda: activity.append(("initialize",))
        fake_pythoncom.CoUninitialize = lambda: activity.append(("uninitialize",))

        with patch.dict(sys.modules, {
            "pythoncom": fake_pythoncom,
            "win32com": fake_win32com,
            "win32com.client": fake_client,
        }), patch.object(bridge.sys, "platform", "win32"):
            sheets = []
            for sheet_name, rows in bridge.iter_open_excel_sheets("C:/example.xlsx"):
                sheets.append((sheet_name, list(rows)))

        self.assertEqual(sheets, [("Office protected sheet", [
            (1, ("Customer", "Group code")),
            (2, ("Example", "88-26004")),
        ])])
        self.assertEqual(instance.AutomationSecurity, 3)
        self.assertFalse(instance.Visible)
        self.assertFalse(instance.EnableEvents)
        self.assertFalse(instance.DisplayAlerts)
        opened = [row[1] for row in activity if row[0] == "open"]
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0]["ReadOnly"])
        self.assertEqual(opened[0]["UpdateLinks"], 0)
        self.assertFalse(opened[0]["AddToMru"])
        self.assertIn(("close", {"SaveChanges": False}), activity)
        self.assertIn(("quit",), activity)
        self.assertEqual(activity[-1], ("uninitialize",))

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
