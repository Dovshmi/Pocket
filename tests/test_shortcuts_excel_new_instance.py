"""Pocket Shortcuts: Excel must open when another workbook is already running."""
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
        self.book = self.root / "separate-workbook.xlsx"
        self.book.write_bytes(b"Office workbook fixture")

    def _com(self, office):
        client = types.ModuleType("win32com.client")
        client.DispatchEx = MagicMock(return_value=office)
        client.Dispatch = MagicMock(
            side_effect=AssertionError("Existing Excel instance must not be reused"))
        win32 = types.ModuleType("win32com")
        win32.__path__ = []
        win32.client = client
        return client, {"win32com": win32, "win32com.client": client}

    def test_excel_xlsx_opens_separate_office_instance(self):
        excel = MagicMock()
        client, imports = self._com(excel)
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, imports), \
                patch.object(shortcuts.os, "startfile", create=True) as start:
            shortcuts.launch_shortcut("file", str(self.book))
        client.DispatchEx.assert_called_once_with("Excel.Application")
        client.Dispatch.assert_not_called()
        self.assertTrue(excel.Visible)
        excel.Workbooks.Open.assert_called_once_with(
            Filename=str(self.book.resolve()))
        start.assert_not_called()
        excel.Quit.assert_not_called()

    def test_multiple_workbook_launches_create_independent_excel_processes(self):
        office1, office2 = MagicMock(), MagicMock()
        client, imports = self._com(office1)
        client.DispatchEx.side_effect = [office1, office2]
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, imports):
            shortcuts.launch_shortcut("file", str(self.book))
            shortcuts.launch_shortcut("file", str(self.book))
        self.assertEqual(client.DispatchEx.call_count, 2)
        office1.Workbooks.Open.assert_called_once()
        office2.Workbooks.Open.assert_called_once()
        self.assertIsNot(office1, office2)

    def test_excel_program_shortcut_starts_new_excel_process(self):
        executable = self.root / "EXCEL.EXE"
        executable.touch()
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.object(shortcuts.os, "startfile", create=True) as start, \
                patch.object(shortcuts.subprocess, "Popen") as popen:
            shortcuts.launch_shortcut("file", str(executable))
        popen.assert_called_once_with([str(executable.resolve()), "/x"])
        start.assert_not_called()

    def test_other_windows_files_keep_shell_association(self):
        pdf = self.root / "report.pdf"
        pdf.touch()
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.object(shortcuts.os, "startfile", create=True) as start:
            shortcuts.launch_shortcut("file", str(pdf))
        start.assert_called_once_with(str(pdf.resolve()))

    def test_excel_without_registered_com_falls_back_to_shell(self):
        client, imports = self._com(MagicMock())
        client.DispatchEx.side_effect = RuntimeError("Excel not registered")
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, imports), \
                patch.object(shortcuts.os, "startfile", create=True) as start:
            shortcuts.launch_shortcut("file", str(self.book))
        start.assert_called_once_with(str(self.book.resolve()))

    def test_excel_open_failure_quits_only_fresh_instance(self):
        office = MagicMock()
        office.Workbooks.Open.side_effect = RuntimeError("Excel permission error")
        client, imports = self._com(office)
        with patch.object(shortcuts.sys, "platform", "win32"), \
                patch.dict(sys.modules, imports), \
                patch.object(shortcuts.os, "startfile", create=True) as start:
            with self.assertRaisesRegex(OSError, "Excel started"):
                shortcuts.launch_shortcut("file", str(self.book))
        office.Quit.assert_called_once_with()
        start.assert_not_called()
        client.Dispatch.assert_not_called()

    def test_normalization_does_not_launch_any_program(self):
        with patch.object(shortcuts.os, "startfile", create=True) as start, \
                patch.object(shortcuts.subprocess, "Popen") as popen:
            normalized = shortcuts.normalize_shortcut("file", str(self.book))
        self.assertTrue(normalized.endswith(".xlsx"))
        start.assert_not_called()
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
