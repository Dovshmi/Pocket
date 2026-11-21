# Pocket Extra — Local + Plain SQLite (Experimental)

This feature is on `experiment/extra-excel-lookup`, not stable `main`.

## Two independent search modes

**Local:** The existing search opens the selected Excel workbook on each search, using the standard openpyxl reader or authorized Microsoft Excel COM for protected books. Local mode is unchanged: no cached rows, no created database, and no saved search history.

**Database:** A fast, normal, unencrypted SQLite database. Searches use an on-disk token index; they **do not open Excel, reload the workbook into RAM, access the Internet, or synchronize automatically**. The database stores all populated Excel columns as readable JSON, the source worksheet and original row number, along with indexed substring and normalized group-code search tokens.

Code searches remain separator tolerant: `8826004`, `88-26004` and `88 26004` match the same group code. Text/IP/VRF/VDOM/VLAN queries search all populated cells.

## Compact Extra interface and Load DB

The **Mini** layout removes the redundant Extra heading, helper descriptions
and excess spacing. Database status is a single line:

`Last sync: DD/MM/YYYY HH:MM · ✓ Success`

or `Last sync: — · ✕ Failed` when the database is inaccessible.
The time is converted from stored UTC to the Windows local time. Customer
data, source paths, database paths and row counts are **not printed** in the
status panel. Other views use the same concise status.

**Load DB** lets you reuse an existing **Pocket Extra SQLite v2** file without
running Sync or opening the source Excel workbook. Supported files are
`.sqlite3`, `.sqlite`, `.db`, and `.db3`. This is a database file import,
**not** execution of arbitrary `.sql` scripts. The selected database stays
unchanged, and Pocket only replaces its current index after schema, row count,
integrity and indexed-search metadata checks pass. Failed/cancelled imports
preserve the previous index. The imported source Excel path can belong to a
different Windows machine; **Database searches do not require the original
Excel source path**. That path is used only by Local mode and new manual Sync.

## How to create or update the database

1. Run Pocket from the experimental ZIP. Choose **Extra → Database**.
2. Select your Excel source using **Browse**.
3. Click **Sync database** and approve the warning about retaining an **unencrypted local copy**. Only sync if your workplace permits storing the source data that way.
4. The sync iterates all sheets. The first manual sync can take time, particularly for IRM-protected workbooks, but later searches do not read Excel.
5. Pocket verifies SQLite metadata, row count and integrity **before** replacing the existing database. Cancelled/failed sync preserves the previous file.
6. Click **Sync database** again whenever you decide to refresh. There is no automatic sync on launch, file change, or search.
7. **Delete DB** deletes only the copied SQLite index after confirmation; the Excel source file is never modified.

**Database path:** For Portable, `Pocket-Portable/data/extra_excel_index.sqlite3`; for installed Pocket, `%APPDATA%\PocketDesk\extra_excel_index.sqlite3`. Keep the entire portable folder on company-approved storage. Do not commit the DB or copy it to GitHub. The file is **not encrypted**; anyone able to read it can see its contents using standard SQLite software.

### Migrating from the old encrypted database

The previous experimental build wrote **schema v1** with Windows DPAPI encryption. This new build writes **schema v2**, with ordinary, unencrypted SQLite.

- A v1 file will display a clear message that manual Sync is required. Pocket does **not** try to decrypt it and does **not** silently delete it.
- Select your original Excel source and run **Sync database** once. A successfully verified new SQLite v2 file atomically replaces the old v1 database.
- If sync fails, the previous file remains untouched. You may keep a backup of the old `data` directory during migration.
- If the old DPAPI credentials are no longer usable, **the source Excel file** is required for the new one-time sync.

## Privacy and accuracy

Only users explicitly authorized to store a **persistent unencrypted copy** should use Database mode. Permission to access an IRM workbook programmatically does not by itself authorize offline plaintext duplication. Pocket makes no network requests for this feature, and the new SQLite file is created only on manual Sync.

The Excel source is always opened read-only without saving. The UI continues to show up to 120 results, each with worksheet and physical row. Normalized group-code matches are searched via a dedicated code token; general substring matching uses an indexed set of two- and three-character tokens. All candidate rows are verified using the existing Local mode matching rules.

The source workbook may have cached formula values rather than recalculated results. `.xlsx`, `.xlsm`, `.xls`, `.xltx`, and `.xltm` are supported; `.xlsb` is not.

In the **Mini Extra** view, outer scrolling, Matches, and All Columns remain scrollable with the mouse wheel/touchpad but their scroll rails are hidden.

## Testing

```powershell
py -3 -m unittest tests.test_extra_excel_db tests.test_extra_excel_lookup -v
```

Synthetic tests verify plain SQLite readability with standard `sqlite3`, existing schema v1 messaging, matching with formatted group codes, manual-only refresh, cancellation and failure recovery, Windows path fallback, and that searches do not touch Excel. Production builds include the SQLite engine from Python and do not require DPAPI for Database mode.
