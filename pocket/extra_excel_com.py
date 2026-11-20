"""Read values from an *already-open* Microsoft Excel workbook (Windows only).

This fallback exists for workbook formats that Excel can decrypt with the user's
existing permissions but that openpyxl cannot decode as a normal ZIP. It does
not open documents, invoke macros, save, export, modify or copy cell contents.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

BATCH_ROWS = 256


class ExcelReadUnavailable(RuntimeError):
    """Excel must be open with the requested book and accessible permissions."""


def _matches_file(selected: Path, opened_name: str) -> bool:
    """Compare mapped-drive and UNC paths safely; never match by basename only."""
    try:
        if os.path.normcase(os.path.abspath(str(selected))) == os.path.normcase(
                os.path.abspath(opened_name)):
            return True
        return os.path.samefile(str(selected), opened_name)
    except (OSError, ValueError):
        return False


def _as_matrix(value, rows: int, columns: int):
    """Normalize Excel's COM scalar/tuple shapes for one-cell or one-row reads."""
    if rows == 1 and columns == 1:
        return ((value,),)
    if rows == 1:
        return (tuple(value),)
    if columns == 1:
        return tuple((v,) if not isinstance(v, (list, tuple)) else tuple(v)
                     for v in value)
    return tuple(tuple(row) for row in value)


def iter_open_excel_sheets(path, *, cancelled=None):
    """Yield (sheet title, physical-row-number iterator) from a visible Excel process.

    The workbook MUST already be open in desktop Excel. COM objects stay in this
    caller thread, which initializes and uninitializes its own COM apartment.
    Windows does not need an admin account; Excel's existing document permissions
    still apply and can prevent this search.
    """
    if sys.platform != "win32":
        raise ExcelReadUnavailable(
            "This workbook needs desktop Microsoft Excel on Windows.")
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ExcelReadUnavailable(
            "Excel integration is unavailable in this Pocket build.") from exc

    pythoncom.CoInitialize()
    try:
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception as exc:
            raise ExcelReadUnavailable(
                "This file may be encrypted or protected. Open it in desktop "
                "Excel first, sign in if prompted, then search in Pocket again."
            ) from exc

        selected = Path(path)
        workbook = None
        try:
            for candidate in excel.Workbooks:
                if cancelled is not None and cancelled():
                    return
                if _matches_file(selected, str(candidate.FullName)):
                    workbook = candidate
                    break
        except Exception as exc:
            raise ExcelReadUnavailable(
                "Excel is running but does not allow access to its open workbooks."
            ) from exc

        if workbook is None:
            raise ExcelReadUnavailable(
                "Pocket cannot find this exact workbook among Excel's open files. "
                "Open the selected file in desktop Excel, then retry. "
                "If the drive is mapped, use the same path shown by Excel."
            )

        try:
            for sheet in workbook.Worksheets:
                if cancelled is not None and cancelled():
                    return

                used = sheet.UsedRange
                start_row, start_col = int(used.Row), int(used.Column)
                nrows, ncols = int(used.Rows.Count), int(used.Columns.Count)
                if nrows < 1 or ncols < 1:
                    continue

                # COM Range.Value2 reads batches rather than making one
                # cross-process COM call per cell (critical for big workbooks).
                def rows_in_sheet(sheet=sheet, start_row=start_row, start_col=start_col,
                                  nrows=nrows, ncols=ncols):
                    for start in range(start_row, start_row + nrows, BATCH_ROWS):
                        if cancelled is not None and cancelled():
                            return
                        last = min(start + BATCH_ROWS - 1, start_row + nrows - 1)
                        segment = sheet.Range(
                            sheet.Cells(start, start_col),
                            sheet.Cells(last, start_col + ncols - 1))
                        block = _as_matrix(segment.Value2, last - start + 1, ncols)
                        for offset, cells in enumerate(block):
                            if cancelled is not None and cancelled():
                                return
                            # Original Excel column positions are preserved.
                            yield start + offset, (None,) * (start_col - 1) + cells

                yield str(sheet.Name), rows_in_sheet()
        except ExcelReadUnavailable:
            raise
        except Exception as exc:
            raise ExcelReadUnavailable(
                "Excel does not allow Pocket to read this workbook through "
                "the current document permissions."
            ) from exc
    finally:
        pythoncom.CoUninitialize()
