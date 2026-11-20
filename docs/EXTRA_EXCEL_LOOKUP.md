# Pocket Extra — Excel lookup (experimental)

Feature branch: `experiment/extra-excel-lookup`. Stable Pocket `main` is unchanged.

## Two search modes

**Local** (default) preserves the existing behavior. Each search reads the selected
Excel workbook directly. Protected files are read through the authorized Microsoft
Excel desktop application, opened invisibly read-only if needed. Local mode **never
creates a database** and does not cache the workbook in RAM.

**Database** searches a **manually created, encrypted SQLite index on disk**, without
opening Excel, reconnecting to a mapped drive or loading the entire source file
into RAM. Results include original sheet, physical row and every populated column.
The same code normalization applies in both modes: `8826004` equals `88-26004`
or `88 26004`. Other fields use case-insensitive substring search.

## Manual sync workflow

1. Go to **Extra** and select **Database**.
2. Choose an Excel source file using **Browse** (or paste its path).
3. Click **Sync database**. Review the explicit warning and continue **only if
   your organization allows a persistent offline copy**.
4. Pocket reads all populated Excel rows and builds an indexed, encrypted SQLite
   database. This initial **manual sync** can be slow for large Excel workbooks.
5. Future searches use SQLite immediately and do not read Excel. Even after
   closing Pocket, the database remains available offline.
6. When the Excel file changes, **you** decide when to press **Sync database**
   again. Search never triggers sync, auto-refresh, loading or rebuilding.
7. **Delete DB** removes the local indexed copy, without changing the Excel file.

If a manual sync fails or is cancelled, the previous completed database is
preserved, and the incomplete temporary database is deleted.

Only **one** workbook is associated with this experimental database. A manually
selected source that does not match its saved source requires another manual sync
before the search uses it.

### Local database location

- **Portable ZIP:** `Pocket-Portable/data/extra_excel_index.sqlite3` beside
  `PocketDesk.exe`; the database is not included in any GitHub artifact.
- **Installed/non-portable:** `%APPDATA%\PocketDesk\extra_excel_index.sqlite3`
  because installation directories are often not writable.

Only the user who created it should be able to decrypt the contents. Moving the
SQLite file to another Windows account/machine will not automatically make the
contents readable. Database paths and sync timestamps are encrypted inside the
database rather than stored in the normal Pocket settings.

## Security and company policy

- **Important:** Microsoft Office IRM *programmatic access* is not necessarily
  authorization to create an independent offline copy. Confirm your organization's
  storage, retention and data-handling policy before pressing Sync.
- Synced row data is encrypted at rest with **Windows DPAPI (current user)**.
  Search postings contain HMAC-protected short search tokens instead of plaintext
  customer names, IP addresses, VRF identifiers or workbook values.
- Encryption does not remove the need to protect the local machine, the
  database, Windows account or authorized backup locations.
- Sync is always opt-in via a warning dialog; Database mode does not write on
  entry, startup, search, or merely selecting a file.
- No workbook data is uploaded to a website, GitHub or any network service by
  Pocket. A source file on a network share is still read through its existing
  Windows/Office permissions **only during Sync** (or Local searches).
- No source Excel file is edited, exported or saved during search or Sync.
  The existing open workbook of the user is never closed.
- Never commit local data directories or copied workplace documents to a repo.

## Limits and implementation

Supported: `.xlsx`, `.xlsm`, `.xls`, `.xltx`, `.xltm`. Not: `.xlsb`.
Workbook formulas show their cached values only. Header detection is heuristic
(top ten rows), with a fallback to column letters. Up to 120 hits are returned
per search; narrow the query if more matches exist.

The database is built by streaming rows and indexing searchable tokens on disk.
It does **not** eagerly load all workbook rows into the application's RAM on the
first search. DPAPI and Excel COM require Windows for protected database mode.

Run focused tests:

```powershell
py -3 -m unittest tests.test_extra_excel_lookup tests.test_extra_excel_db -v
```

The GitHub repository contains only synthetic sample data, never a workplace
workbook, synced database, user credentials or personal search history.
