"""Pocket Extra SQLite lookup: explicit offline snapshots, never automatic sync.

All workbook values are encrypted with Windows DPAPI for the current user.
Search postings are keyed HMAC digrams/trigrams, not plaintext cell values.
Only the Sync action reads a workbook; searching queries SQLite on disk.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from zipfile import is_zipfile

from . import extra_excel_lookup as lookup
from . import portable_storage

FILE_NAME = "extra_excel_index.sqlite3"
SCHEMA_VERSION = "1"
WRITE_BATCH = 750


class DatabaseUnavailable(RuntimeError):
    pass


class WindowsUserCodec:
    """Windows per-user encryption. Fail closed instead of storing plaintext."""
    def __init__(self):
        try:
            import win32crypt
        except ImportError as exc:
            raise DatabaseUnavailable(
                "Database requires Windows DPAPI (pywin32) in Pocket.") from exc
        self.api = win32crypt

    def seal(self, clear: bytes) -> bytes:
        return self.api.CryptProtectData(
            clear, "Pocket Extra local encrypted database", None, None, None, 0)[1]

    def open(self, encrypted: bytes) -> bytes:
        return self.api.CryptUnprotectData(encrypted, None, None, None, 0)[1]


def database_path() -> Path:
    # Portable: beside EXE at Pocket-Portable/data. Installed: per-user AppData.
    return portable_storage.data_directory() / FILE_NAME


def _secret_token(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), "sha256").digest()[:16]


def _grams(value: str, n: int):
    return {value[i:i+n] for i in range(len(value) - n + 1)} if len(value) >= n else set()


def _record_terms(fields, key: bytes):
    """At most one posting per record and token; full values never enter SQLite."""
    values = [lookup.normalize_text(val) for _, val in fields]
    postings = set()
    for value in values:
        for n in (2, 3):
            for gram in _grams(value, n):
                postings.add(_secret_token(key, f"g{n}:{gram}"))
    for _, raw in fields:
        code = lookup.normalize_group_code(raw)
        if code:
            postings.add(_secret_token(key, "code:" + code))
    return postings


def _query_terms(query: str, key: bytes):
    normalized = lookup.normalize_text(query)
    n = 2 if len(normalized) == 2 else 3
    grams = _grams(normalized, n)
    return sorted(_secret_token(key, f"g{n}:{gram}") for gram in grams)


def _source_sheets(path, cancelled):
    path = Path(path)
    # The same Excel COM fallback as Local; unlike Local, consume *all* rows.
    if path.suffix.lower() == ".xls":
        yield from lookup._xls_sheets(path)
    elif is_zipfile(path):
        yield from lookup._xlsx_sheets(path)
    else:
        from .extra_excel_com import iter_open_excel_sheets
        yield from iter_open_excel_sheets(path, cancelled=cancelled)


def _readonly_connection(path):
    """Open an existing SQLite database without writing or creating anything.

    The portable Pocket folder may live on a mapped network drive. On Windows,
    Path.resolve().as_uri() can become file://server/share/... which SQLite
    rejects as an unsupported URI authority. Try the canonical URI first,
    then a native Windows filename, without ever running write statements.
    """
    path = Path(path)
    if not path.is_file():
        raise DatabaseUnavailable("No database exists. Press Sync to create one.")
    errors = []
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro",
                                     uri=True, timeout=4)
        connection.execute("PRAGMA query_only=ON")
        return connection
    except (sqlite3.Error, ValueError, OSError) as exc:
        errors.append(exc)
        try:
            connection.close()
        except (NameError, UnboundLocalError):
            pass

    # Windows has valid native UNC/mapped paths that fail SQLite URI parsing.
    # File existence is checked again to avoid creating files on a missing path.
    if not path.is_file():
        raise DatabaseUnavailable("Database file is missing.") from errors[-1]
    try:
        connection = sqlite3.connect(str(path), timeout=4)
        connection.execute("PRAGMA query_only=ON")
        return connection
    except sqlite3.Error as exc:
        try:
            connection.close()
        except (NameError, UnboundLocalError):
            pass
        raise DatabaseUnavailable(
            "Cannot open local database (SQLite: " +
            (getattr(exc, "sqlite_errorname", None) or type(exc).__name__) +
            "). Check the folder permissions and disk availability."
        ) from exc


def _safe_db_error(exc):
    """Return diagnostic SQL error code without leaking file names or data."""
    code = getattr(exc, "sqlite_errorname", None)
    return " (" + code + ")" if code else " (" + type(exc).__name__ + ")"


def _metadata(connection, name, codec):
    row = connection.execute(
        "SELECT payload FROM meta WHERE key = ?", (name,)).fetchone()
    if row is None:
        raise DatabaseUnavailable("Database metadata is missing; re-sync.")
    return codec.open(row[0])


def _init_schema(connection):
    connection.executescript("""
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=FULL;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE meta(key TEXT PRIMARY KEY, payload BLOB NOT NULL);
        CREATE TABLE rows_data(
            row_id INTEGER PRIMARY KEY,
            content BLOB NOT NULL
        );
        CREATE TABLE postings(
            token BLOB NOT NULL,
            row_id INTEGER NOT NULL,
            PRIMARY KEY(token, row_id)
        ) WITHOUT ROWID;
    """)
    connection.execute("INSERT INTO metadata VALUES (?, ?)",
                       ("schema", SCHEMA_VERSION))


def read_info(db_path=None, *, codec=None):
    """Return tiny metadata only; never preload results or access the workbook."""
    path = Path(db_path) if db_path is not None else database_path()
    if not path.is_file():
        return None
    cipher = codec if codec is not None else WindowsUserCodec()
    try:
        with closing(_readonly_connection(path)) as connection:
            schema = connection.execute(
                "SELECT value FROM metadata WHERE key='schema'").fetchone()
            if not schema or schema[0] != SCHEMA_VERSION:
                raise DatabaseUnavailable("Unknown database format; re-sync.")
            details = json.loads(_metadata(connection, "details", cipher))
            return details
    except (sqlite3.DatabaseError, ValueError, UnicodeError) as exc:
        raise DatabaseUnavailable(
            "Database cannot be read" + _safe_db_error(exc) +
            ". The original Excel workbook is unaffected.") from exc
    except Exception as exc:
        if isinstance(exc, DatabaseUnavailable):
            raise
        raise DatabaseUnavailable(
            "Cannot decrypt database with this Windows account.") from exc


def _linked_path(path):
    return os.path.normcase(os.path.abspath(str(Path(path).expanduser())))


def same_source(path, db_info):
    """Compare exact files, tolerating Windows short-name and mapped-path aliases."""
    if not path:
        return True
    if _linked_path(path) == _linked_path(db_info["source"]):
        return True
    try:
        return os.path.samefile(str(path), db_info["source"])
    except (OSError, ValueError):
        return False


def sync_database(source_path, db_path=None, *, cancelled=None,
                  on_progress=None, codec=None):
    """Manually replace an encrypted, indexed snapshot, atomically on success.

    Never called by search or startup. On error/cancellation preserve prior DB.
    """
    source = Path(source_path).expanduser()
    if source.suffix.lower() not in lookup.SUPPORTED_EXTENSIONS:
        raise ValueError("Choose a supported Excel workbook before Sync.")
    if not source.is_file():
        raise FileNotFoundError("Selected Excel workbook was not found.")
    if source.stat().st_size == 0:
        raise ValueError("Selected Excel workbook is empty.")
    target = Path(db_path) if db_path is not None else database_path()
    cipher = codec if codec is not None else WindowsUserCodec()
    if cancelled is not None and cancelled():
        return None
    # Only a deliberate Sync may create data directory or SQLite file.
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".pocket-extra-", suffix=".sqlite3",
                                        dir=str(target.parent))
    os.close(handle)
    connection = None
    rows = 0
    try:
        connection = sqlite3.connect(temporary, timeout=5)
        _init_schema(connection)
        secret = secrets.token_bytes(32)
        connection.execute("INSERT INTO meta VALUES (?, ?)",
                           ("secret", cipher.seal(secret)))
        records = []
        tokens = []
        with connection:
            for sheet_name, sheet_rows in _source_sheets(source, cancelled):
                first = []
                row_iterator = iter(sheet_rows)
                from itertools import islice, chain
                first = list(islice(row_iterator, 10))
                header_number, headers = lookup._headings(first)
                for row_number, row in chain(first, row_iterator):
                    if cancelled is not None and cancelled():
                        return None
                    if row_number == header_number:
                        continue
                    fields = lookup._columns(row, headers)
                    if not fields:
                        continue
                    rows += 1
                    record = {"sheet": str(sheet_name), "row": int(row_number),
                              "fields": fields}
                    blob = cipher.seal(json.dumps(
                        record, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8"))
                    records.append((rows, blob))
                    tokens.extend((term, rows) for term in _record_terms(fields, secret))
                    if len(records) >= WRITE_BATCH:
                        connection.executemany(
                            "INSERT INTO rows_data (row_id, content) VALUES (?, ?)",
                            records)
                        connection.executemany(
                            "INSERT OR IGNORE INTO postings (token, row_id) VALUES (?, ?)",
                            tokens)
                        records.clear()
                        tokens.clear()
                        if on_progress is not None:
                            on_progress(rows)
                if on_progress is not None:
                    on_progress(rows)
            if records:
                connection.executemany(
                    "INSERT INTO rows_data (row_id, content) VALUES (?, ?)",
                    records)
                connection.executemany(
                    "INSERT OR IGNORE INTO postings (token, row_id) VALUES (?, ?)",
                    tokens)
            if cancelled is not None and cancelled():
                return None
            details = {"source": str(source.resolve()),
                       "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "rows": rows}
            connection.execute("INSERT INTO meta VALUES (?, ?)",
                               ("details", cipher.seal(
                                   json.dumps(details, ensure_ascii=False).encode("utf-8"))))
        connection.close()
        connection = None
        if cancelled is not None and cancelled():
            return None
        # The old index is untouched until the new database passes a complete
        # metadata read and SQLite's on-disk consistency check. This catches
        # filesystem/SQLite failures before the only destructive replace step.
        verified = read_info(temporary, codec=cipher)
        if verified is None or verified.get("rows") != rows:
            raise DatabaseUnavailable("New database did not pass verification.")
        with closing(_readonly_connection(temporary)) as verification:
            integrity = verification.execute("PRAGMA quick_check(1)").fetchone()
            if not integrity or integrity[0] != "ok":
                raise DatabaseUnavailable(
                    "New database failed integrity check; previous index preserved.")
        os.replace(temporary, target)
        return details
    finally:
        if connection is not None:
            connection.close()
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass


def search_database(query, db_path=None, *, limit=lookup.MAX_RESULTS,
                    cancelled=None, codec=None):
    """Run indexed substring/exact-code search against SQLite only.

    No workbook access. No whole-database RAM load. Decrypt only candidate rows.
    """
    path = Path(db_path) if db_path is not None else database_path()
    if not path.is_file():
        raise DatabaseUnavailable("No database yet. Select a workbook and press Sync.")
    if not 1 <= limit <= 1000:
        raise ValueError("Invalid search limit.")
    text = lookup.normalize_text(query)
    if len(text) < 2:
        return [], False
    cipher = codec if codec is not None else WindowsUserCodec()
    hits = []
    try:
        with closing(_readonly_connection(path)) as connection:
            key = _metadata(connection, "secret", cipher)
            tokens = _query_terms(query, key)
            code = lookup.normalize_group_code(query)
            code_token = _secret_token(key, "code:" + code) if code else None
            if not tokens and code_token is None:
                return [], False
            if len(tokens) > 900:
                # Avoid SQLite placeholder limits, prefer searching via smaller
                # distinctive ngram subset; final match is exact in Python.
                tokens = tokens[:900]

            # All query ngrams must occur in candidate row, in any fields;
            # final match_quality ensures the substring is in one actual cell.
            candidates = []
            if tokens:
                placeholders = ",".join("?" for _ in tokens)
                sql = (f"SELECT row_id FROM postings WHERE token IN ({placeholders}) "
                       "GROUP BY row_id HAVING COUNT(*) = ?")
                candidates.append((sql, (*tokens, len(tokens))))
            if code_token is not None:
                candidates.insert(0, ("SELECT row_id FROM postings WHERE token=?", (code_token,)))
            seen = set()
            for sql, params in candidates:
                for (record_id,) in connection.execute(sql, params):
                    if cancelled is not None and cancelled():
                        return [], False
                    if record_id in seen:
                        continue
                    seen.add(record_id)
                    record = connection.execute(
                        "SELECT content FROM rows_data WHERE row_id=?", (record_id,)).fetchone()
                    if record is None:
                        continue
                    obj = json.loads(cipher.open(record[0]))
                    fields = tuple((str(a), str(b)) for a, b in obj["fields"])
                    match = tuple(name for name, val in fields
                                  if lookup.match_quality(query, val))
                    if not match:
                        continue
                    exact = any(lookup.match_quality(query, val) == 2
                                for _, val in fields)
                    hits.append(lookup.ExcelHit(obj["sheet"], obj["row"],
                                                fields, match, exact))
                    if len(hits) > limit:
                        return sorted(hits[:limit], key=lambda x: not x.exact), True
            return sorted(hits, key=lambda x: not x.exact), False
    except sqlite3.DatabaseError as exc:
        raise DatabaseUnavailable(
            "Database search failed" + _safe_db_error(exc) +
            ". Verify the database before attempting another Sync.") from exc


def delete_database(db_path=None):
    """Explicit delete action only. No silent deletion of prior snapshots."""
    path = Path(db_path) if db_path is not None else database_path()
    if path.exists():
        path.unlink()
        return True
    return False
