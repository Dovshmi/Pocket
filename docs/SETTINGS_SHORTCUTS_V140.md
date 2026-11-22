# Pocket v1.40 — Shortcuts, menus and Settings

Source: v1.40.0 in `main`, developed in `experiment/extra-excel-lookup`. The latest published stable Windows ZIP/EXE remains v1.39.9 until a separate v1.40.0 release.

## Mini menu bar: direct management

- **Left-click** opens the selected tool.
- **Drag** one real Pocket icon onto another to reorder. Changes save automatically; no separate Edit/Save/Cancel view.
- **Right-click → Hide** removes a tool from the toolbar, without deleting any notes, settings or other saved tool data.
- **Green Add (+)** shows the hidden tools. Choosing one enables it and **appends it last** in the saved order. Users may drag it afterward.
- At **seven or fewer** active menus, the Add tile follows them, if anything is hidden. At **eight or more**, More/Less occupies the eighth slot and the Add tile appears at the end of the expanded row.
- **Settings** can be reordered but cannot be hidden. More/Less and Add are functional controls, not draggable tool icons.

Menu order and visibility save locally, are included in Settings backup/restore, and can be reset using Reset preferences → Menus. Existing profiles missing menu-order settings use the original default order.

## Settings: compact Show / Hide below Appearance

There are seven collapsible categories. **Show / Hide** is immediately below Appearance (also in the Dashboard Settings column); it contains a simple two-column list, **not** a duplicate reorder editor or live preview.

- **Green icon = menu currently enabled/visible**; its `−` label means clicking will **hide** it.
- **Red icon = menu currently disabled/hidden**; its `+` label means clicking will **add** it at the **end**.
- Settings itself is always present and is not an option to hide.
- Each change is committed automatically. There is no Save button.
- Only one settings category expands at a time; closing a category does not modify preferences.

Other categories retain their functionality: Appearance, Shortcuts & launcher, Clipboard, Quick Slots & Translate, Network & Extra, and Backup & Restore. The Settings footer displays v1.40.

## Shortcuts: Excel reuse by exact file path

Clicking an Excel workbook shortcut (`.xlsx`, `.xls`, `.xlsm`, `.xlsb` and supported templates) uses Office COM when available:

1. Pocket checks open Excel workbooks by **complete canonical path** (including the running-object table for other Excel instances when accessible).
2. If the **same workbook is already open**, Pocket activates that workbook instead of opening a duplicate. Windows foreground restrictions can still prevent the window from being raised after Excel activates it.
3. If the requested workbook is **different**, Pocket uses an existing Excel application if available and opens that file.
4. If Excel is not already running, Pocket creates an Excel application instance for the requested workbook.
5. If COM is unavailable before opening, the original Windows file-association fallback remains. If Office itself rejects opening a workbook, Pocket reports an error and does not close any pre-existing Excel application.

A shortcut pointing to `EXCEL.EXE` itself still launches Excel with `/x`. No workbook is opened, edited or saved merely by viewing the Shortcuts menu. Existing Office security and permission prompts remain. Other files, folders and web shortcuts retain their original behavior.

## Mini Extra: results and mouse scrolling

- **Matches:** Up/Down keys change the selected result; a slim dark vertical scrollbar at the right allows dragging through the result list.
- **Wheel over Matches:** scrolls the **outer Pocket page** rather than the Matches rows, avoiding unintentional loss of the currently visible result.
- **Selected Row:** Left/Right keys navigate between results when the details area has focus.
- Local Excel search, manual offline SQLite sync, Outlook SOC unsent drafts, and the other Excel actions are unchanged.

## Testing and caveats

GitHub Actions exercises unit tests on Windows and Linux with Python 3.11/3.13; GUI smoke tests cover Mini, Normal and Dashboard, menu ordering/visibility, arrow and wheel navigation, and the production-style portable EXE launch. Test fixtures and Office mocks use synthetic data.

**Actual corporate Excel/Outlook integration must also be checked on the intended work PC**: different concurrently open workbooks, the same workbook activated again, protected workbooks, and classic Outlook or default mail configuration cannot be fully reproduced in CI. The local SQLite index and backup ZIPs are **unencrypted** and must be kept on organization-approved storage. No private workbook or customer dataset is included with the app.
