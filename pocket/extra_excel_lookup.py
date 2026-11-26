"""Read-only, offline search of Excel workbooks for Pocket Extra.

No workbook writes, temporary files, search-history persistence or network calls.
The caller owns the result lifetime. Large XLSX/XLSM files stream worksheet rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import chain, islice
from pathlib import Path
from zipfile import BadZipFile
import re
import unicodedata

SUPPORTED_EXTENSIONS = frozenset({".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"})
MAX_RESULTS = 120
_CODE_PATTERN = re.compile(r"^[0-9\s\-\u2010-\u2015\u2212/._]+$")
_DIGITS = re.compile(r"\D+")


@dataclass(frozen=True)
class ExcelHit:
    sheet: str
    row: int
    fields: tuple[tuple[str, str], ...]
    matched_columns: tuple[str, ...]
    exact: bool = False


def display_value(value) -> str:
    """Keep rendered values legible without changing the source workbook."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value).strip()


def normalize_text(raw) -> str:
    value = unicodedata.normalize("NFKC", display_value(raw))
    return " ".join(value.replace("\u200e", "").replace("\u200f", "").casefold().split())


def normalize_group_code(raw) -> str | None:
    """8826004, 88-26004 and 88 26004 are equivalent, not arbitrary IPs."""
    value = normalize_text(raw)
    if not _CODE_PATTERN.fullmatch(value) or value.count(".") > 1:
        # Dotted IPv4 addresses are not group codes.
        return None
    digits = _DIGITS.sub("", value)
    return digits if len(digits) >= 4 else None


def match_quality(query: str, cell: str) -> int:
    """2=exact (including normalized group code), 1=substring, 0=no hit."""
    target, current = normalize_text(query), normalize_text(cell)
    if not target or not current:
        return 0
    if target == current:
        return 2
    code_query, code_cell = normalize_group_code(query), normalize_group_code(cell)
    if code_query is not None and code_query == code_cell:
        return 2
    return 1 if target in current else 0


def _headings(first_rows):
    """Locate the likely header among the first ten physical worksheet rows."""
    candidates = []
    for row_number, row in first_rows:
        values = [display_value(v) for v in row if display_value(v)]
        if len(values) < 3:
            continue
        labels = sum(bool(re.search(r"[^\W\d_]", value, flags=re.UNICODE))
                     for value in values)
        if labels >= 3:
            candidates.append((labels * 2 + len(values), -row_number, row_number, row))
    if not candidates:
        return 0, ()
    _score, _first, number, headers = max(candidates)
    return number, tuple(display_value(v) for v in headers)


def _column_name(index):
    """Excel column letters, 1-based, including columns past Z."""
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _columns(row, headers):
    fields = []
    for index, raw in enumerate(row, start=1):
        value = display_value(raw)
        if not value:
            continue
        letter = _column_name(index)
        label = headers[index - 1] if index <= len(headers) else ""
        fields.append((f"{label} ({letter})" if label else f"Column {letter}", value))
    return tuple(fields)


def _xlsx_sheets(path, *, on_total=None):
    from openpyxl import load_workbook
    workbook = load_workbook(filename=str(path), read_only=True,
                             data_only=True, keep_links=False)
    try:
        if on_total is not None:
            sizes = [sheet.max_row for sheet in workbook.worksheets]
            on_total(sum(sizes) if all(n is not None for n in sizes) else None)
        for sheet in workbook.worksheets:
            yield sheet.title, enumerate(sheet.iter_rows(values_only=True), start=1)
    finally:
        workbook.close()


def _xls_sheets(path, *, on_total=None):
    import xlrd
    workbook = xlrd.open_workbook(str(path), on_demand=True)
    try:
        if on_total is not None:
            on_total(sum(workbook.sheet_by_index(i).nrows for i in range(workbook.nsheets)))
        for index in range(workbook.nsheets):
            sheet = workbook.sheet_by_index(index)

            def rows(sheet=sheet):
                for row_number in range(sheet.nrows):
                    values = sheet.row_values(row_number)
                    for cell_index, value in enumerate(values):
                        if sheet.cell_type(row_number, cell_index) == xlrd.XL_CELL_DATE:
                            try:
                                values[cell_index] = xlrd.xldate_as_datetime(
                                    value, workbook.datemode)
                            except (ValueError, OverflowError):
                                pass
                    yield row_number + 1, values

            yield sheet.name, rows()
    finally:
        workbook.release_resources()


def _scan_sheets(iterator, query, limit, cancelled):
    """Reuse exactly the same search semantics for ZIP and desktop-Excel rows."""
    hits = []
    try:
        for sheet_name, rows in iterator:
            if cancelled is not None and cancelled():
                return [], False
            first = list(islice(rows, 10))
            header_number, headers = _headings(first)
            for row_number, row in chain(first, rows):
                if cancelled is not None and cancelled():
                    return [], False
                if row_number == header_number:
                    continue
                fields = _columns(row, headers)
                if not fields:
                    continue
                matching = [(name, match_quality(query, value)) for name, value in fields]
                matches = tuple(name for name, quality in matching if quality)
                if not matches:
                    continue
                exact = any(quality == 2 for _, quality in matching)
                hits.append(ExcelHit(sheet_name, row_number, fields, matches, exact))
                if len(hits) >= limit:
                    return sorted(hits, key=lambda hit: not hit.exact), True
        return sorted(hits, key=lambda hit: not hit.exact), False
    finally:
        iterator.close()


def search_workbook(path, query, *, limit=MAX_RESULTS, cancelled=None):
    """Search workbook locally. Fall back to a *running* Excel for protected XLSX.

    Modern XLSX files are normally ZIP archives. Some managed/IRM-encrypted
    files are OLE containers despite the .xlsx extension; only desktop Excel
    signed into the authorized work account can display their contents.
    """
    path = Path(path).expanduser()
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Choose an Excel .xlsx, .xlsm or .xls workbook.")
    if not path.is_file():
        raise FileNotFoundError("The selected Excel workbook is unavailable.")
    if path.stat().st_size == 0:
        raise ValueError("The Excel workbook is empty.")
    if not normalize_text(query):
        return [], False
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Result limit must be positive.")

    iterator = _xls_sheets(path) if path.suffix.lower() == ".xls" else _xlsx_sheets(path)
    try:
        return _scan_sheets(iterator, query, limit, cancelled)
    except BadZipFile:
        # Never decrypt, export, cache or try to bypass workbook permissions.
        # Attach ONLY to the exact workbook already open in desktop Excel.
        from .extra_excel_com import iter_open_excel_sheets
        if cancelled is not None and cancelled():
            return [], False
        return _scan_sheets(iter_open_excel_sheets(path, cancelled=cancelled),
                            query, limit, cancelled)
