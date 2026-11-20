"""Pocket Extra: fast, manually synced plain SQLite database.

Database mode never opens Excel or copies a workbook into RAM when searching.
Sync is explicitly user-triggered, leaves the source workbook untouched, and
atomically replaces the previous index ONLY after integrity verification.
This database is NOT encrypted. Store it in an approved location.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from itertools import chain, islice
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from zipfile import is_zipfile

from . import extra_excel_lookup as lookup
from . import portable_storage

FILE_NAME = "extra_excel_index.sqlite3"
SCHEMA_VERSION = "2"
WRITE_BATCH = 300
MAX_QUERY_TERMS = 750


class DatabaseUnavailable(RuntimeError):
    """A database cannot be opened, needs a new Sync, or is inaccessible."""


def database_path() -> Path:
    # Portable: Pocket-Portable/data. Installed: per-user %APPDATA%/PocketDesk.
    return portable_storage.data_directory() / FILE_NAME


def _grams(value: str, n: int):
    if len(value) < n:
        return set()
    return {value[i:i + n] for i in range(len(value) - n + 1)}


def _record_terms(fields):
    """Casefolded substring search tokens and normalized exact group codes."""
    postings = set()
    for _, value in fields:
        normalized = lookup.normalize_text(value)
        for length in (2, 3):
            for gram in _grams(normalized, length):
                postings.add(f"g{length}:{gram}")
        code = lookup.normalize_group_code(value)
        if code:
            postings.add("code:" + code)
    return postings


def _query_terms(query: str):
    normalized = lookup.normalize_text(query)
    length = 2 if len(normalized) == 2 else 3
    grams = _grams(normalized, length)
    return sorted(f"g{length}:{gram}" for gram in grams)[:MAX_QUERY_TERMS]


def _source_sheets(path, cancelled):
    """Reuse the tested Local Excel reader, including protected Office COM."""
    path = Path(path)
    if path.suffix.lower() == ".xls":
        yield from lookup._xls_sheets(path)
    elif is_zipfile(path):
        yield from lookup._xlsx_sheets(path)
    else:
        from .extra_excel_com import iter_open_excel_sheets
        yield from iter_open_excel_sheets(path, cancelled=cancelled)


def _readonly_connection(path):
    """Never create a database during search, including on mapped drives.

    SQLite URI form can fail with a UNC authority; retry with the native path
    and SQLite query_only flag. No schema changes or synchronization are run.
    """
    path = Path(path)
    if not path.is_file():
        raise DatabaseUnavailable("No database yet. Choose Excel and press Sync database.")
    try:
        con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro",
                              uri=True, timeout=5)
        try:
            con.execute("PRAGMA query_only=ON")
            return con
        except Exception:
            con.close()
            raise
    except (sqlite3.Error, OSError, ValueError):
        if not path.is_file():
            raise DatabaseUnavailable("Database is missing. Press Sync database.")
        try:
            con = sqlite3.connect(str(path), timeout=5)
            try:
                con.execute("PRAGMA query_only=ON")
                return con
            except Exception:
                con.close()
                raise
        except sqlite3.Error as exc:
            raise DatabaseUnavailable(
                "Cannot open SQLite database. Check the Pocket data folder and permissions."
            ) from exc


def _schema_version(con):
    try:
        record = con.execute(
            "SELECT value FROM metadata WHERE key = 'schema'").fetchone()
    except sqlite3.DatabaseError as exc:
        raise DatabaseUnavailable(
            "Database format cannot be read. Use Sync database to rebuild it.") from exc
    if record is None:
        raise DatabaseUnavailable("Database metadata missing. Use Sync database.")
    if record[0] == "1":
        raise DatabaseUnavailable(
            "This is an OLD encrypted database. Click Sync database once to "
            "create a new plain SQLite database. Local mode still works.")
    if record[0] != SCHEMA_VERSION:
        raise DatabaseUnavailable(
            "Unsupported database version. Use Sync database to rebuild it.")


def read_info(db_path=None):
    """Read only tiny metadata; never open Excel or load indexed rows into RAM."""
    path = Path(db_path) if db_path is not None else database_path()
    if not path.is_file():
        return None
    try:
        with closing(_readonly_connection(path)) as con:
            _schema_version(con)
            data = dict(con.execute("SELECT key, value FROM metadata"))
            info = {
                "source": data["source"],
                "updated_at": data["updated_at"],
                "rows": int(data["rows"]),
            }
            if info["rows"] < 0:
                raise ValueError("Invalid row count")
            return info
    except (sqlite3.Error, KeyError, ValueError, TypeError) as exc:
        raise DatabaseUnavailable(
            "Database metadata is invalid. Use Sync database to rebuild it.") from exc


def _linked_path(path):
    return os.path.normcase(os.path.abspath(str(Path(path).expanduser())))


def same_source(path, db_info):
    if not path:
        return True
    if _linked_path(path) == _linked_path(db_info["source"]):
        return True
    try:
        return os.path.samefile(str(path), db_info["source"])
    except (OSError, ValueError):
        return False


def _init_schema(con):
    con.executescript("""
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=FULL;
        PRAGMA temp_store=FILE;
        PRAGMA cache_size=-8192;
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE rows_data (
            row_id INTEGER PRIMARY KEY,
            content TEXT NOT NULL
        );
        CREATE TABLE postings (
            token TEXT NOT NULL,
            row_id INTEGER NOT NULL,
            PRIMARY KEY (token, row_id)
        ) WITHOUT ROWID;
    """)
    con.execute("INSERT INTO metadata(key,value) VALUES ('schema', ?)",
                (SCHEMA_VERSION,))


def sync_database(source_path, db_path=None, *, cancelled=None, on_progress=None):
    """Explicit user-requested full sync with atomic replacement.

    Existing (even legacy encrypted) index is preserved on failure/cancel.
    The new index stores plaintext JSON rows plus a substring token index.
    """
    source = Path(source_path).expanduser()
    if source.suffix.lower() not in lookup.SUPPORTED_EXTENSIONS:
        raise ValueError("Choose a supported Excel file for Sync database.")
    if not source.is_file():
        raise FileNotFoundError("The selected Excel workbook was not found.")
    if source.stat().st_size == 0:
        raise ValueError("The selected Excel workbook is empty.")
    target = Path(db_path) if db_path is not None else database_path()
    if cancelled is not None and cancelled():
        return None

    # No file or directory is created by searching, opening Extra, or Local mode.
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".pocket-extra-",
                                        suffix=".sqlite3", dir=str(target.parent))
    os.close(handle)
    con = None
    rows_count = 0
    try:
        con = sqlite3.connect(temporary, timeout=10)
        _init_schema(con)
        row_batch, token_batch = [], []

        # Every commit is to a disposable temporary database, never the source
        # workbook or the previous index. This bounds SQLite transaction size.
        def flush():
            if not row_batch:
                return
            with con:
                con.executemany(
                    "INSERT INTO rows_data(row_id, content) VALUES (?, ?)", row_batch)
                con.executemany(
                    "INSERT OR IGNORE INTO postings(token, row_id) VALUES (?, ?)",
                    token_batch)
            row_batch.clear()
            token_batch.clear()

        with closing(_source_sheets(source, cancelled)) as sheets:
            for sheet_name, sheet_rows in sheets:
                headers_and_rows = iter(sheet_rows)
                first = list(islice(headers_and_rows, 10))
                header_number, headers = lookup._headings(first)
                for row_number, row in chain(first, headers_and_rows):
                    if cancelled is not None and cancelled():
                        return None
                    if row_number == header_number:
                        continue
                    fields = lookup._columns(row, headers)
                    if not fields:
                        continue
                    rows_count += 1
                    item = {"sheet": str(sheet_name), "row": int(row_number),
                            "fields": fields}
                    row_batch.append((
                        rows_count, json.dumps(item, ensure_ascii=False,
                                               separators=(",", ":"))))
                    token_batch.extend(
                        (token, rows_count) for token in _record_terms(fields))
                    if len(row_batch) >= WRITE_BATCH:
                        flush()
                        if on_progress is not None:
                            on_progress(rows_count)
                if on_progress is not None:
                    on_progress(rows_count)

        if cancelled is not None and cancelled():
            return None
        flush()
        details = {
            "source": str(source.resolve()),
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rows": rows_count,
        }
        with con:
            con.executemany("INSERT INTO metadata(key,value) VALUES (?, ?)",
                            [(key, str(value)) for key, value in details.items()])
        con.close()
        con = None
        if cancelled is not None and cancelled():
            return None

        # Never replace an existing database until the new one passes
        # a complete on-disk validation via the normal search/read path.
        verified = read_info(temporary)
        if verified is None or verified["rows"] != rows_count:
            raise DatabaseUnavailable(
                "New SQLite database failed metadata validation. Old database preserved.")
        with closing(_readonly_connection(temporary)) as validation:
            check = validation.execute("PRAGMA quick_check(1)").fetchone()
            count = validation.execute("SELECT COUNT(*) FROM rows_data").fetchone()
            if not check or check[0] != "ok" or count[0] != rows_count:
                raise DatabaseUnavailable(
                    "New SQLite database failed integrity check. Old database preserved.")
        if cancelled is not None and cancelled():
            return None
        os.replace(temporary, target)
        return details
    finally:
        if con is not None:
            con.close()
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass


def search_database(query, db_path=None, *, limit=lookup.MAX_RESULTS,
                    cancelled=None):
    """Fast on-disk indexed search. Does not use Excel, DPAPI or in-memory cache."""
    path = Path(db_path) if db_path is not None else database_path()
    if not path.is_file():
        raise DatabaseUnavailable("No database yet. Press Sync database once.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ValueError("Invalid result limit.")
    normalized = lookup.normalize_text(query)
    if len(normalized) < 2:
        return [], False
    hits = []
    try:
        with closing(_readonly_connection(path)) as con:
            _schema_version(con)
            tokens = _query_terms(query)
            code = lookup.normalize_group_code(query)
            code_token = "code:" + code if code else None
            queries = []
            # Exact normalized group codes first, so formatting is irrelevant.
            if code_token:
                queries.append((
                    "SELECT row_id FROM postings WHERE token=?", (code_token,)))
            if tokens:
                placeholders = ",".join("?" for _ in tokens)
                queries.append((
                    f"SELECT row_id FROM postings WHERE token IN ({placeholders}) "
                    "GROUP BY row_id HAVING COUNT(*) = ?",
                    (*tokens, len(tokens))))

            seen = set()
            for sql, params in queries:
                for (record_id,) in con.execute(sql, params):
                    if cancelled is not None and cancelled():
                        return [], False
                    if record_id in seen:
                        continue
                    seen.add(record_id)
                    row = con.execute(
                        "SELECT content FROM rows_data WHERE row_id=?",
                        (record_id,)).fetchone()
                    if row is None:
                        continue
                    item = json.loads(row[0])
                    fields = tuple((str(k), str(v)) for k, v in item["fields"])
                    matching = tuple(k for k, v in fields
                                     if lookup.match_quality(query, v))
                    if not matching:
                        continue
                    exact = any(lookup.match_quality(query, v) == 2
                                for _, v in fields)
                    hits.append(lookup.ExcelHit(item["sheet"], item["row"],
                                                fields, matching, exact))
                    if len(hits) > limit:
                        return sorted(hits[:limit], key=lambda x: not x.exact), True
        return sorted(hits, key=lambda x: not x.exact), False
    except (sqlite3.DatabaseError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise DatabaseUnavailable(
            "SQLite search failed. Try manual Sync database. "
            "The Excel source was not modified.") from exc


def delete_database(db_path=None):
    """Delete only the indexed database after explicit user confirmation."""
    path = Path(db_path) if db_path is not None else database_path()
    if path.exists():
        path.unlink()
        return True
    return False
