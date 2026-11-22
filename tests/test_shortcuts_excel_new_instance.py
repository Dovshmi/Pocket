"""Regression tests for Windows Excel shortcuts: reuse exact open workbook.

Opening a different XLSX uses the existing Excel application where available.
Never call GetObject(filename), which can open a new copy unexpectedly.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from pocket import shortcut_utils as shortcuts


class ExcelShortcutLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.book = self.root / "original.xlsx"
        self.book.write_bytes(b"test fixture")
        self.another = self.root / "different.xlsx"
        self.another.write_bytes(b"other test fixture")

    def _client(self, active=None, *, no_active=False):
        client = types.ModuleType("win32com.client")
        client.GetActiveObject = MagicMock(
            side_effect=RuntimeError("Excel not running") if no_active else None,
            return_value=active)
        client.DispatchEx = MagicMock(return_value=MagicMock())
        client.GetObject = MagicMock(side_effect=AssertionError(
            "GetObject(path) may create a workbook, never use it"))
        client.Dispatch = MagicMock()
        win32 = types.ModuleType("win32com")
        win32.__path__ = []
        win32.client = client
        return client, {"win32com": win32, "win32com.client": client}

    def _run_file(self, path, modules):
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, modules), \
                patch.object(shortcuts.os, "startfile", create=True) as shell:
            shortcuts.launch_shortcut("file", str(path))
        shell.assert_not_called()

    def _book(self, path, app):
        item = MagicMock()
        item.FullName = str(path)
        item.Application = app
        return item

    def test_exact_open_workbook_activates_instead_of_opening_copy(self):
        excel = MagicMock()
        book = self._book(self.book, excel)
        excel.Workbooks = [book]
        client, modules = self._client(excel)
        self._run_file(self.book, modules)
        book.Activate.assert_called_once()
        self.assertTrue(excel.Visible)
        client.DispatchEx.assert_not_called()
        client.GetObject.assert_not_called()

    def test_matching_case_insensitive_path(self):
        self.assertTrue(shortcuts._same_excel_file(
            str(self.book).upper(), str(self.book)))
        self.assertFalse(shortcuts._same_excel_file(
            str(self.another), str(self.book)))

    def test_different_workbook_opens_in_existing_excel_not_duplicate(self):
        excel = MagicMock()
        book = self._book(self.book, excel)
        newbook = self._book(self.another, excel)
        excel.Workbooks = [book]
        excel.Workbooks.Open.return_value = newbook
        client, modules = self._client(excel)
        self._run_file(self.another, modules)
        excel.Workbooks.Open.assert_called_once_with(Filename=str(self.another.resolve()))
        newbook.Activate.assert_called_once()
        book.Activate.assert_not_called()
        client.DispatchEx.assert_not_called()

    def test_no_excel_process_creates_instance_for_first_file(self):
        client, modules = self._client(no_active=True)
        fresh = client.DispatchEx.return_value
        newbook = self._book(self.book, fresh)
        fresh.Workbooks.Open.return_value = newbook
        self._run_file(self.book, modules)
        client.DispatchEx.assert_called_once_with("Excel.Application")
        fresh.Workbooks.Open.assert_called_once_with(Filename=str(self.book.resolve()))
        fresh.Quit.assert_not_called()
        newbook.Activate.assert_called_once()

    def test_rot_can_activate_exact_file_in_another_excel_process(self):
        # Current Excel instance holds a DIFFERENT workbook; the requested
        # workbook appears in a second Excel process via COM running table.
        current = MagicMock()
        current.Workbooks = [self._book(self.another, current)]
        client, modules = self._client(current)
        running = MagicMock()
        moniker = MagicMock()
        moniker.GetDisplayName.return_value = str(self.book)
        enumeration = MagicMock()
        enumeration.Next.side_effect = [(moniker,), ()]
        running.EnumRunning.return_value = enumeration
        running.GetObject.return_value = object()
        target_app = MagicMock()
        exact = self._book(self.book, target_app)
        client.Dispatch.return_value = exact
        pythoncom = types.ModuleType("pythoncom")
        pythoncom.GetRunningObjectTable = lambda: running
        pythoncom.CreateBindCtx = lambda n: MagicMock()
        modules["pythoncom"] = pythoncom
        self._run_file(self.book, modules)
        exact.Activate.assert_called_once()
        current.Workbooks.Open.assert_not_called()
        client.DispatchEx.assert_not_called()

    def test_rot_rejects_nonidentical_file_path(self):
        current = MagicMock()
        current.Workbooks = []
        newbook = self._book(self.book, current)
        current.Workbooks.Open.return_value = newbook
        client, modules = self._client(current)
        running = MagicMock()
        moniker = MagicMock()
        moniker.GetDisplayName.return_value = str(self.another)
        enumeration = MagicMock()
        enumeration.Next.side_effect = [(moniker,), ()]
        running.EnumRunning.return_value = enumeration
        pythoncom = types.ModuleType("pythoncom")
        pythoncom.GetRunningObjectTable = lambda: running
        pythoncom.CreateBindCtx = lambda n: MagicMock()
        modules["pythoncom"] = pythoncom
        self._run_file(self.book, modules)
        client.Dispatch.assert_not_called()
        current.Workbooks.Open.assert_called_once()

    def test_excel_program_shortcut_starts_separate_process(self):
        exe = self.root / "EXCEL.EXE"
        exe.touch()
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.object(shortcuts.os, "startfile", create=True) as shell, \
                patch.object(shortcuts.subprocess, "Popen") as popen:
            shortcuts.launch_shortcut("file", str(exe))
        popen.assert_called_once_with([str(exe.resolve()), "/x"])
        shell.assert_not_called()

    def test_non_excel_shortcuts_still_use_windows_file_association(self):
        other = self.root / "document.pdf"
        other.touch()
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.object(shortcuts.os, "startfile", create=True) as shell:
            shortcuts.launch_shortcut("file", str(other))
        shell.assert_called_once_with(str(other.resolve()))

    def test_com_unavailable_uses_existing_windows_fallback(self):
        client, modules = self._client(no_active=True)
        client.DispatchEx.side_effect = RuntimeError("Office not installed")
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, modules), \
                patch.object(shortcuts.os, "startfile", create=True) as shell:
            shortcuts.launch_shortcut("file", str(self.book))
        shell.assert_called_once_with(str(self.book.resolve()))

    def test_failed_open_does_not_quit_preexisting_excel(self):
        excel = MagicMock()
        excel.Workbooks = []
        excel.Workbooks.Open.side_effect = RuntimeError("Permission denied")
        client, modules = self._client(excel)
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, modules):
            with self.assertRaises(OSError):
                shortcuts.launch_shortcut("file", str(self.book))
        excel.Quit.assert_not_called()
        client.DispatchEx.assert_not_called()

    def test_failed_open_only_quits_newly_created_instance(self):
        client, modules = self._client(no_active=True)
        fresh = client.DispatchEx.return_value
        fresh.Workbooks.Open.side_effect = RuntimeError("Permission denied")
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, modules):
            with self.assertRaises(OSError):
                shortcuts.launch_shortcut("file", str(self.book))
        fresh.Quit.assert_called_once()

    def test_normalization_never_launches_excel(self):
        client, modules = self._client()
        with patch.dict(sys.modules, modules), \
                patch.object(shortcuts.os, "startfile", create=True) as shell:
            self.assertEqual(shortcuts.normalize_shortcut("file", str(self.book)),
                             str(self.book.resolve()))
        shell.assert_not_called()
        client.GetActiveObject.assert_not_called()


if __name__ == "__main__":
    unittest.main()
