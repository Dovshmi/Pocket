# Pocket Extra — Local + Plain SQLite (v1.40.0)

This feature is included in the v1.40.0 `main` source. The earlier `experiment/extra-excel-lookup` branch and experimental preview ZIP are retained separately; the latest officially published stable Windows binary remains v1.39.9 until v1.40.0 release validation.

## Latest v1.40 Mini MATCHES scrolling

- Mini MATCHES includes a slim dark **8px draggable scrollbar** on the right.
- Wheel/touchpad gestures over the results scroll the Pocket page instead of
  moving the result list itself.
- Up/Down still navigates Matches; Left/Right inside Selected Row also works.
- Normal/Dashboard result scrolling and database search are unchanged.

## SOC Outlook draft from one selected result

After a Local or Database search, select the exact customer row under **Matches**
and click **Outlook · SOC** beside the selected-row details. Pocket prepares a
**new, unsent** Outlook draft (no recipient, attachments, auto-save or sending).

The subject follows:
`(customer / business name) (line code) פנייה לSOC`

Only the chosen row is used. The draft includes:

- **שם העסק / הלקוח** — pulled from the customer/business column.
- **קוד קו** — pulled from the actual line/circuit column, for example
  `קוד קישור`. The `קוד קבוצה` column is **not** treated as a line code.
- **כתובת FortiGate** — derived conservatively from the FG sheet name:
  `FG25` → `10.238.2.25`, `FG-2.8-METRO1` → `10.238.2.8`.
  An ambiguous or non-FG sheet leaves the address for the user to complete.
- **VDOM** — from the selected row's VDOM column.
- **איש קשר**, **מספר טלפון**, **תיאור התקלה / הבקשה**,
  **מספר פנייה קודמת (אם קיימת)**, and
  **באישור מומחה – שם המומחה** — **blank placeholders to fill in Outlook**.

If any of the first four automatic fields are missing, Pocket asks the user
whether to open the draft anyway and clearly marks missing values for manual
completion. No email, recipient address, contact phone, specialist approval
name, or problem description is stored back in Pocket.

Classic desktop Outlook uses an unsent COM MailItem with an RTL Hebrew body
and the existing Outlook signature preserved. When classic Outlook COM is
unavailable (e.g. New Outlook), Pocket opens the registered Windows `mailto:`
handler. Set Outlook as the default mail app in Windows for that fallback.

The source Excel workbook and plain SQLite database are never modified by
the SOC draft function. The user reviews and sends the final message manually.

## Two independent search modes

**Local:** The existing search opens the selected Excel workbook on each search, using the standard openpyxl reader or authorized Microsoft Excel COM for protected books. Local mode is unchanged: no cached rows, no created database, and no saved search history.

**Database:** A fast, normal, unencrypted SQLite database. Searches use an on-disk token index; they **do not open Excel, reload the workbook into RAM, access the Internet, or synchronize automatically**. The database stores all populated Excel columns as readable JSON, the source worksheet and original row number, along with indexed substring and normalized group-code search tokens.

Code searches remain separator tolerant: `8826004`, `88-26004` and `88 26004` match the same group code. Text/IP/VRF/VDOM/VLAN queries search all populated cells.

## v1.40 — Final Excel Source alignment

The Extra filename is aligned with its last-sync label without moving Browse.
The vertical spacing between the read-only filename row, database metadata,
and Sync/Load DB/Delete row is slightly smaller in Mini. No database or
source-file semantics have changed; sync remains manual.

## v1.40 — Mini keyboard navigation and merged database controls

- **Matches:** Up/Down arrows navigate results while the list is focused. The Selected Row updates immediately. The row count is shown on the right side of the MATCHES heading rather than in an always-reserved status row beneath Smart Search.
- **Selected Row:** With this panel focused, Right/Left arrows navigate next/previous matches, while the Outlook draft button always uses the chosen hit. No new arrow buttons or icons.
- **Excel Source:** The selected Excel filename and Browse remain on one line. In Database mode only, last-sync metadata and existing Sync/Load DB/Delete controls appear directly underneath inside the same bordered Excel Source card. There is no independent DATABASE panel. Local mode stays small.
- **Failures and progress:** Compact feedback is visible in the MATCHES header; hovering it shows the full status or error text. No search status line takes up space while idle.
- Data and permissions are unchanged: database creation is always manual, destructive actions still require confirmation, no Excel workbook is modified, and an offline database is readable unencrypted SQLite.

## Pocket v1.40 — Compact Extra

The selected Excel source is now **one read-only row**: a muted filename
(“Excel · Extranet_2026.xlsx”) and **Browse** on its right. Hover the
filename to see the complete local path. There is no editable Excel-path
input; select or change workbooks using Browse. No source path is saved
between Pocket sessions, as before.

**Matches is unchanged.** The Selected Row block now shows a compact,
two-column quick view with the customer/business name, line/circuit code,
group code, VDOM, VRF, FortiGate management IP, and FG VLAN. The
FortiGate management IP is derived from the FG worksheet name by the
existing SOC lookup rules, not from the customer public IP. Click the IP
to copy it. If it cannot be safely inferred, Pocket shows a dash rather
than guessing.

The **Show other columns (N)** button reveals every remaining populated
Excel field *in its original column order*, using a bounded inner
scroll area. No Excel columns are discarded. The disclosure's open/closed
choice persists when navigating between matched rows within the current
Pocket session and is closed by default.

The selected-row quick view, the SOC draft button, and both Local and
Database lookup paths reuse the same in-memory search results. Database
schema remains v2; **no manual Sync or new SQLite import is required** for
the interface change. The synced database stays in Pocket's local data
folder, unchanged.

Settings displays **Version v1.40** in the v1.40.0 source, and the
portable build package is versioned v1.40.0. The v1.39.9 stable downloads
remain available until a separately validated stable v1.40.0 Windows release.



Extra Mini keeps the controls focused on fast daily lookup:

- **MODE: Live / Offline** — one keyboard-accessible switch aligned to the
  right between **Local** (live Excel) and **Database** (offline index).
- Under the Excel path field a single muted hint explains the expected file,
  e.g. `Extranet_2026.xlsx`. It is an example, not a hardcoded filename.
- **Sync** stays aligned left, while **Load DB** and **Delete** sit to the right.
- Settings displays an **Extra · Database** section only while an active local
  SQLite file exists. It shows the canonical active filename/path and includes
  **Copy path**. The original imported .db file itself is never changed.

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

1. Run Pocket from a v1.40.0 source/portable build or clearly labeled experimental ZIP. Choose **Extra → Database**.
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
