"""Regression tests for plain SQLite Extra mode (no DPAPI, no automatic sync)."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import Workbook

from pocket import extra_excel_db as db


class ExtraDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.book = self.folder / "public-fixture.xlsx"
        self.index = self.folder / "test-index.sqlite3"
        book = Workbook()
        a = book.active
        a.title = "FG-23"
        a.append(("Customer", "Group code", "IP", "VRF"))
        a.append(("Example Customer", "88-26004", "10.20.30.0/29", "branch-vrf"))
        a.append(("Second Customer", "88-28020", "10.20.40.0/29", "site-vrf"))
        a.append(("Example Duplicate", "88 26004", "10.20.41.0/29", "branch-vrf"))
        b = book.create_sheet("FG-METRO")
        b.append(("לקוח", "קבוצה", "VDOM"))
        b.append(("לקוח לדוגמה", 8826004, "segmento"))
        book.save(self.book)
        book.close()

    def sync(self, **kwargs):
        return db.sync_database(self.book, self.index, **kwargs)

    def test_only_manual_sync_creates_sqlite_file(self):
        self.assertIsNone(db.read_info(self.index))
        with self.assertRaises(db.DatabaseUnavailable):
            db.search_database("8826004", self.index)
        self.assertFalse(self.index.exists())
        details = self.sync()
        self.assertEqual(details["rows"], 4)
        self.assertTrue(self.index.is_file())

    def test_plain_sqlite_is_readable_without_windows_or_crypto(self):
        self.sync()
        with sqlite3.connect(self.index) as con:
            meta = dict(con.execute("SELECT key, value FROM metadata"))
            self.assertEqual(meta["schema"], "2")
            self.assertEqual(int(meta["rows"]), 4)
            self.assertIn("public-fixture.xlsx", meta["source"])
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM rows_data").fetchone()[0], 4)
            text = con.execute("SELECT content FROM rows_data "
                               "WHERE row_id=1").fetchone()[0]
            self.assertIsInstance(text, str)
            self.assertIn("Example Customer", text)
            self.assertIn("88-26004", text)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM postings "
                "WHERE token='code:8826004'").fetchone()[0], 3)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        info = db.read_info(self.index)
        self.assertEqual(info["rows"], 4)
        self.assertTrue(db.same_source(self.book, info))
        self.assertFalse(db.same_source(self.folder / "other.xlsx", info))

    def test_fast_search_does_not_access_excel_or_reload_all_rows(self):
        self.sync()
        # Fail if an ordinary Database search tries to read the source workbook.
        with patch.object(db, "_source_sheets", side_effect=AssertionError(
                "Database search reopened Excel")):
            hits, capped = db.search_database("8826004", self.index)
            self.assertFalse(capped)
            self.assertEqual(len(hits), 3)
            self.assertTrue(all(x.exact for x in hits))
            self.assertEqual({x.sheet for x in hits}, {"FG-23", "FG-METRO"})
            self.assertEqual(len(db.search_database("88-26004", self.index)[0]), 3)
            self.assertEqual(len(db.search_database("88 26004", self.index)[0]), 3)
            self.assertEqual(len(db.search_database("10.20.30", self.index)[0]), 1)
            self.assertEqual(len(db.search_database("EXAMPLE CUSTOMER", self.index)[0]), 1)
            self.assertEqual(len(db.search_database("לקוח לדוגמה", self.index)[0]), 1)
            self.assertEqual(len(db.search_database("branch-vrf", self.index)[0]), 2)
            self.assertEqual(
                [(x.sheet, x.row) for x in
                 db.search_database("88-28020", self.index)[0]],
                [("FG-23", 3)])
        # Show all nonblank columns and physical row numbers, as in Local mode.
        found = db.search_database("8826004", self.index)[0][0]
        self.assertTrue(found.fields)
        self.assertIsInstance(found.row, int)
        self.assertTrue(found.matched_columns)

    def test_existing_encrypted_v1_is_identified_not_decrypted_or_deleted(self):
        with sqlite3.connect(self.index) as con:
            con.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)")
            con.execute("INSERT INTO metadata VALUES('schema', '1')")
        original = self.index.read_bytes()
        with self.assertRaisesRegex(db.DatabaseUnavailable, "OLD encrypted database"):
            db.read_info(self.index)
        with self.assertRaisesRegex(db.DatabaseUnavailable, "OLD encrypted database"):
            db.search_database("88-26004", self.index)
        self.assertEqual(self.index.read_bytes(), original)
        updated = self.sync()
        self.assertEqual(updated["rows"], 4)
        self.assertEqual(db.read_info(self.index)["rows"], 4)
        self.assertEqual(len(db.search_database("88-26004", self.index)[0]), 3)

    def test_failed_and_cancelled_sync_preserve_existing_snapshot(self):
        self.sync()
        original = self.index.read_bytes()
        with patch.object(db, "_source_sheets", side_effect=RuntimeError(
                "Excel unavailable")):
            with self.assertRaisesRegex(RuntimeError, "Excel unavailable"):
                self.sync()
        self.assertEqual(self.index.read_bytes(), original)
        self.assertFalse(list(self.folder.glob(".pocket-extra-*.sqlite3")))

        tracker = {"rows": 0}
        def report(n):
            tracker["rows"] = n
        result = self.sync(cancelled=lambda: tracker["rows"] >= 2,
                           on_progress=report)
        self.assertIsNone(result)
        self.assertEqual(self.index.read_bytes(), original)
        self.assertFalse(list(self.folder.glob(".pocket-extra-*.sqlite3")))

    def test_sync_replaces_snapshot_only_when_user_requests(self):
        self.sync()
        wb = Workbook()
        sheet = wb.active
        sheet.append(("Customer", "Group code", "VRF"))
        sheet.append(("Replacement", "88-40000", "new-vrf"))
        wb.save(self.book)
        wb.close()
        self.assertEqual(len(db.search_database("88-26004", self.index)[0]), 3)
        self.assertEqual(self.sync()["rows"], 1)
        self.assertEqual(len(db.search_database("88-26004", self.index)[0]), 0)
        self.assertEqual(len(db.search_database("8840000", self.index)[0]), 1)

    def test_sqlite_uri_failure_falls_back_to_native_windows_path(self):
        self.sync()
        original_connect = sqlite3.connect
        modes = []
        def fake_connect(filename, *args, **kwargs):
            uri = bool(kwargs.get("uri", False))
            modes.append(uri)
            if uri:
                raise sqlite3.OperationalError("invalid uri authority: network-host")
            return original_connect(filename, *args, **kwargs)
        with patch.object(db.sqlite3, "connect", side_effect=fake_connect):
            self.assertEqual(db.read_info(self.index)["rows"], 4)
            self.assertEqual(len(db.search_database("8826004", self.index)[0]), 3)
        self.assertIn(True, modes)
        self.assertIn(False, modes)

    def test_no_implicit_creation_and_explicit_delete(self):
        missing = self.folder / "absent.sqlite3"
        self.assertIsNone(db.read_info(missing))
        with self.assertRaises(db.DatabaseUnavailable):
            db._readonly_connection(missing)
        self.assertFalse(missing.exists())
        self.sync()
        hits, limited = db.search_database("branch-vrf", self.index, limit=1)
        self.assertEqual(len(hits), 1)
        self.assertTrue(limited)
        hits, limited = db.search_database(
            "branch-vrf", self.index, cancelled=lambda: True)
        self.assertEqual(hits, [])
        self.assertFalse(limited)
        self.assertTrue(db.delete_database(self.index))
        self.assertFalse(self.index.exists())
        self.assertFalse(db.delete_database(self.index))

    def test_many_rows_sync_and_search_bounded_results(self):
        wb = Workbook()
        sheet = wb.active
        sheet.append(("Customer", "Group code", "Address", "VRF"))
        for index in range(1800):
            sheet.append((f"Sample Client {index}", f"88-{20000+index}",
                          f"10.22.{index//256}.{index%256}", "long-vrf"))
        wb.save(self.book)
        wb.close()
        self.assertEqual(self.sync()["rows"], 1800)
        hits, capped = db.search_database("long-vrf", self.index)
        self.assertEqual(len(hits), db.lookup.MAX_RESULTS)
        self.assertTrue(capped)
        hits, capped = db.search_database("88-21799", self.index)
        self.assertEqual(len(hits), 1)
        self.assertFalse(capped)


if __name__ == "__main__":
    unittest.main()
