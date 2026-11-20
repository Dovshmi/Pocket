"""Pocket Extra encrypted SQLite: no Excel access during database search."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import Workbook

from pocket import extra_excel_db as db


class TestCodec:
    """Deterministic test-only reversible transformation, never used in Pocket."""
    def seal(self, raw: bytes) -> bytes:
        return b"test-sealed:" + bytes(x ^ 0xA5 for x in raw)

    def open(self, wrapped: bytes) -> bytes:
        if not wrapped.startswith(b"test-sealed:"):
            raise ValueError("invalid test ciphertext")
        return bytes(x ^ 0xA5 for x in wrapped[len(b"test-sealed:"):])


class ExtraDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.book = self.folder / "public-fixture.xlsx"
        self.index = self.folder / "test-index.sqlite3"
        self.codec = TestCodec()
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

    def test_no_database_is_ever_created_implicitly(self):
        self.assertIsNone(db.read_info(self.index, codec=self.codec))
        with self.assertRaises(db.DatabaseUnavailable):
            db.search_database("8826004", self.index, codec=self.codec)
        self.assertFalse(self.index.exists())

    def test_explicit_sync_fast_index_and_encrypted_contents(self):
        expected = db.sync_database(self.book, self.index, codec=self.codec)
        self.assertEqual(expected["rows"], 4)
        info = db.read_info(self.index, codec=self.codec)
        self.assertEqual(info["rows"], 4)
        self.assertTrue(db.same_source(self.book, info))
        self.assertFalse(db.same_source(self.folder / "another.xlsx", info))

        raw = self.index.read_bytes()
        for secret in (b"Example Customer", b"88-26004", b"segmento",
                       b"10.20.30.0/29", b"branch-vrf"):
            self.assertNotIn(secret, raw, f"Value leaked into database: {secret}")

        # Repeated database searches never open the source workbook.
        with patch.object(db, "_source_sheets", side_effect=AssertionError(
                "Search tried to open Excel")):
            hits, capped = db.search_database("8826004", self.index, codec=self.codec)
            self.assertFalse(capped)
            self.assertEqual(len(hits), 3)
            self.assertTrue(all(hit.exact for hit in hits))
            self.assertEqual({hit.sheet for hit in hits}, {"FG-23", "FG-METRO"})
            self.assertEqual(len(db.search_database(
                "10.20.30", self.index, codec=self.codec)[0]), 1)
            self.assertEqual(len(db.search_database(
                "EXAMPLE CUSTOMER", self.index, codec=self.codec)[0]), 1)
            self.assertEqual(len(db.search_database(
                "לקוח לדוגמה", self.index, codec=self.codec)[0]), 1)
            self.assertEqual(len(db.search_database(
                "branch-vrf", self.index, codec=self.codec)[0]), 2)
            exact, _ = db.search_database("88-28020", self.index, codec=self.codec)
            self.assertEqual([(x.sheet, x.row) for x in exact], [("FG-23", 3)])

    def test_existing_database_falls_back_when_sqlite_uri_is_rejected(self):
        """Network/mapped Windows directories can fail SQLite's URI authority."""
        import sqlite3
        db.sync_database(self.book, self.index, codec=self.codec)
        original_connect = sqlite3.connect
        calls = []

        def mocked_connect(target, *args, **kwargs):
            calls.append((str(target), bool(kwargs.get("uri", False))))
            if kwargs.get("uri"):
                raise sqlite3.OperationalError("invalid uri authority: network-host")
            return original_connect(target, *args, **kwargs)

        with patch.object(db.sqlite3, "connect", side_effect=mocked_connect):
            info = db.read_info(self.index, codec=self.codec)
            self.assertEqual(info["rows"], 4)
            hits, limited = db.search_database("88-26004", self.index,
                                               codec=self.codec)
            self.assertFalse(limited)
            self.assertEqual(len(hits), 3)
        self.assertTrue(any(uri for _, uri in calls))
        self.assertTrue(any(not uri for _, uri in calls))
        self.assertTrue(self.index.is_file())

    def test_database_reads_do_not_create_files(self):
        missing = self.folder / "absent.sqlite3"
        self.assertIsNone(db.read_info(missing, codec=self.codec))
        with self.assertRaises(db.DatabaseUnavailable):
            db.search_database("88-26004", missing, codec=self.codec)
        with self.assertRaises(db.DatabaseUnavailable):
            db._readonly_connection(missing)
        self.assertFalse(missing.exists())

    def test_cancel_sync_keeps_existing_database_unmodified(self):
        db.sync_database(self.book, self.index, codec=self.codec)
        previous = self.index.read_bytes()
        called = {"rows": 0}
        def cancel():
            return called["rows"] >= 2
        def progress(n):
            called["rows"] = n
        # A short test workbook yields a per-sheet progress callback.
        result = db.sync_database(self.book, self.index, codec=self.codec,
                                  cancelled=cancel, on_progress=progress)
        self.assertIsNone(result)
        self.assertEqual(self.index.read_bytes(), previous)
        self.assertEqual(db.read_info(self.index, codec=self.codec)["rows"], 4)
        self.assertFalse(list(self.folder.glob(".pocket-extra-*.sqlite3")))

    def test_manual_resync_replaces_old_records(self):
        db.sync_database(self.book, self.index, codec=self.codec)
        wb = Workbook()
        ws = wb.active
        ws.append(("Customer", "Group code", "VRF"))
        ws.append(("Replacement", "88-40000", "new-vrf"))
        wb.save(self.book)
        wb.close()
        # Nothing changes until user clicks Sync explicitly.
        self.assertEqual(len(db.search_database(
            "88-26004", self.index, codec=self.codec)[0]), 3)
        info = db.sync_database(self.book, self.index, codec=self.codec)
        self.assertEqual(info["rows"], 1)
        self.assertEqual(len(db.search_database(
            "88-26004", self.index, codec=self.codec)[0]), 0)
        self.assertEqual(len(db.search_database(
            "8840000", self.index, codec=self.codec)[0]), 1)

    def test_limit_cancel_and_delete(self):
        db.sync_database(self.book, self.index, codec=self.codec)
        hits, limited = db.search_database("branch-vrf", self.index,
                                           codec=self.codec, limit=1)
        self.assertEqual(len(hits), 1)
        self.assertTrue(limited)
        hits, limited = db.search_database(
            "branch-vrf", self.index, codec=self.codec,
            cancelled=lambda: True)
        self.assertEqual(hits, [])
        self.assertFalse(limited)
        self.assertTrue(db.delete_database(self.index))
        self.assertFalse(self.index.exists())
        self.assertFalse(db.delete_database(self.index))


if __name__ == "__main__":
    unittest.main()
