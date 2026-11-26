"""Read a protected workbook via authorized local Excel automation (Windows).

Standard XLSX is handled without Office elsewhere. This fallback uses Excel's
own authorized IRM viewer. Pocket never changes, saves, exports, copies to disk,
or transmits workbook data. A book already open in Excel is never closed by us.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

BATCH_ROWS = 256
_MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3


class ExcelReadUnavailable(RuntimeError):
    """Desktop Excel or document permissions disallow this lookup."""


def _matches_file(selected: Path, opened_name: str) -> bool:
    try:
        if os.path.normcase(os.path.abspath(str(selected))) == os.path.normcase(
                os.path.abspath(opened_name)):
            return True
        return os.path.samefile(str(selected), opened_name)
    except (OSError, ValueError):
        return False


def _as_matrix(value, rows: int, columns: int):
    """Normalize Excel COM Value2 scalar/row/column shapes."""
    if rows == 1 and columns == 1:
        return ((value,),)
    if rows == 1:
        return (tuple(value),)
    if columns == 1:
        return tuple((v,) if not isinstance(v, (list, tuple)) else tuple(v)
                     for v in value)
    return tuple(tuple(row) for row in value)


def _find_open_book(excel, selected, cancelled=None):
    try:
        for candidate in excel.Workbooks:
            if cancelled is not None and cancelled():
                return None
            if _matches_file(selected, str(candidate.FullName)):
                return candidate
    except Exception:
        # A different Office session/integrity level may be inaccessible.
        # Do not change or close any workbook in that session.
        return None
    return None


def iter_open_excel_sheets(path, *, cancelled=None, on_total=None):
    """Yield (sheet name, (physical row, values)) from Excel without saving.

    Prefer an exact already-open workbook; otherwise create a separate hidden
    Excel instance and open the selected file ReadOnly. Uses the signed-in Office
    account and respects IRM. Some enterprise configurations may require an
    interactive sign-in, or may forbid Excel automation altogether.
    """
    if sys.platform != "win32":
        raise ExcelReadUnavailable(
            "Protected workbooks require Microsoft Excel on Windows.")
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ExcelReadUnavailable(
            "Microsoft Excel automation is not installed in this Pocket build.") from exc

    pythoncom.CoInitialize()
    excel = None
    workbook = None
    created_excel = False
    opened_workbook = False
    try:
        selected = Path(path)
        if cancelled is not None and cancelled():
            return

        try:
            active_excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            active_excel = None

        if active_excel is not None:
            workbook = _find_open_book(active_excel, selected, cancelled)
            if workbook is not None:
                excel = active_excel
        if cancelled is not None and cancelled():
            return

        if workbook is None:
            # Dedicated instance: never turn off events, macros, notifications
            # or other preferences in the user's already-running Excel.
            try:
                excel = win32com.client.DispatchEx("Excel.Application")
                created_excel = True
                excel.Visible = False
                excel.DisplayAlerts = False
                excel.EnableEvents = False
                excel.AutomationSecurity = _MSO_AUTOMATION_SECURITY_FORCE_DISABLE
                excel.AskToUpdateLinks = False
                if cancelled is not None and cancelled():
                    return
                workbook = excel.Workbooks.Open(
                    Filename=str(selected), UpdateLinks=0, ReadOnly=True,
                    IgnoreReadOnlyRecommended=True, AddToMru=False, Notify=False)
                opened_workbook = True
            except Exception as exc:
                raise ExcelReadUnavailable(
                    "Excel could not open this protected workbook silently. "
                    "Check that Microsoft Excel is installed, you are signed in "
                    "with your authorized work account, and Office permits "
                    "programmatic access. If sign-in is needed, open the file "
                    "in Excel once and try again."
                ) from exc

        try:
            if on_total is not None:
                total = 0
                for sheet in workbook.Worksheets:
                    if cancelled is not None and cancelled():
                        return
                    total += int(sheet.UsedRange.Rows.Count)
                on_total(total)
            for sheet in workbook.Worksheets:
                if cancelled is not None and cancelled():
                    return
                used = sheet.UsedRange
                start_row, start_col = int(used.Row), int(used.Column)
                nrows, ncols = int(used.Rows.Count), int(used.Columns.Count)
                if nrows < 1 or ncols < 1:
                    continue

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
                            yield start + offset, (None,) * (start_col - 1) + cells

                yield str(sheet.Name), rows_in_sheet()
        except ExcelReadUnavailable:
            raise
        except Exception as exc:
            raise ExcelReadUnavailable(
                "Excel refused to read this workbook. Check the signed-in "
                "account and the workbook's IRM programmatic-access rights."
            ) from exc
    finally:
        # Only close the workbook and Excel process created by Pocket.
        # Never close or save a document that the user opened themselves.
        if opened_workbook and workbook is not None:
            try:
                workbook.Close(SaveChanges=False)
            except Exception:
                pass
        if created_excel and excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()
