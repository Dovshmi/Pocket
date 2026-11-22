# Pocket v1.40 — Shortcuts & Settings refinements

Experimental branch: `experiment/extra-excel-lookup`. Stable `main` remains unchanged.

## Shortcuts: Microsoft Excel when Excel is already open

Pocket previously relied exclusively on the Windows file association (`os.startfile`) for all files. For Excel, Windows may forward the request to an existing Excel instance and silently leave the requested file unopened. In v1.40:

- Clicking an Excel workbook shortcut (`.xlsx`, `.xls`, `.xlsm`, `.xlsb`, or related Excel workbook/template extensions) uses the installed Excel COM automation interface to create a **separate Excel instance** and open the selected file.
- Clicking a shortcut pointing directly at `EXCEL.EXE` starts Excel with `/x`, requesting a separate instance.
- Office permission and security prompts are not suppressed. Workbooks are not saved, modified or opened by merely displaying the Shortcuts menu.
- If Microsoft Excel COM is not installed or cannot initialize, workbook shortcuts use the original Windows default-file-opening fallback.
- If Excel opens but the workbook itself fails to load, Pocket shows an error and closes **only the new** instance it started, without touching existing Excel windows.
- Other files, folders and web shortcuts retain their original behavior.

This requires an installed, usable Microsoft Excel application for the separate-instance path. It does not install Excel or bypass workplace document protection.

## Settings: condensed category navigation

Settings now uses **seven collapsible, keyboard-focusable categories**. Only the active category displays its controls, so Mini does not present a very long list of toggles by default.

| Category | Preserved options |
|---|---|
| Appearance | Normal/Mini/Dashboard layout and all six themes |
| Shortcuts & launcher | Global hotkey, Quick Search, Extra Mini launcher enable and customization |
| Visible tools | Every tool menu toggle, arranged in two concise columns |
| Clipboard | Capture pause, sensitive filter, RAM/DB history limits and retention |
| Quick Slots & Translate | Enable, paste/copy behavior, notification settings, modifier shortcuts, Hebrew-English conversion and hotkey |
| Network & Extra | Windows proxy and the active Excel SQLite database file |
| Backup & Restore | Selective backup, restore and reset preferences |

- Every existing widget and handler is still created. Collapsing a category only hides its view; **no preference is reset, deleted or migrated**.
- All categories use the original app callbacks, and settings still save automatically.
- A category can be opened by mouse or keyboard; opening another category closes the previous one. The last-open category is remembered during the current Pocket session.
- Theme and display-mode pickers use small grids, with the current choice highlighted.
- Visible tools use compact toggle tiles, with keyboard focus and a tooltip explaining each tool.
- Settings still displays `v1.40` and retains the existing backup/privacy notices.

## Direct Mini toolbar management (latest v1.40 preview)

There is **no separate Menu Order editor or Show/Hide grid in Settings**. The live Mini navigation bar itself is the editor:

- Left-click: open the selected tool normally.
- Drag an actual tool icon over another icon: change its place immediately and auto-save (no extra Edit mode or Save/Cancel).
- Right-click a tool: **Hide Menu**. The Settings icon is movable but never hideable.
- Green **Add (+)**: click for a menu of currently hidden tools; choose one to restore it in its saved position.
- **More/Less**: when there are eight or more active menu icons (including Settings), More occupies the eighth slot and opens the extra rows. Add remains the final icon of the expanded rows only while a hidden menu exists.
- Seven or fewer active icons: there is no need for More; the green Add tile follows the icons (at the eighth slot when seven are active). If all menus are visible, the Add icon is absent.

The visibility list and order remain in the same local Settings data and are included in Settings backup/restore. No migration of existing profiles is necessary. Reset → Menus still restores the original arrangement and visibility.

Normal and Dashboard continue to read the same saved ordering; the Normal Settings access icon stays anchored to the edge. Offline-first behavior and all non-menu Settings options are unchanged.

## Legacy menu-order note (superseded)

The older Settings-based Menu Order editor and preview below are no longer displayed in the application. They are retained in earlier pre-release builds only.

## Menu Order: visual drag-and-drop, local persistence and backups

Settings → **Visible Tools** now begins with a compact real-icon editor and a live Mini layout preview. Drag an icon onto another position, or click one icon and then the destination. Keyboard focus with Return or Space also selects icons. A Reset order action restores the default ordering. The special More/Less tile always occupies the last slot of Mini's first row when needed, and cannot be moved. All tool icons—including Settings—can be placed in the Mini bar. Normal's Settings entry remains fixed at the right edge to guarantee access, but the order of the other Normal icons follows the preference; Dashboard tool navigation follows the saved order. The independent Extra Mini quick slots are unchanged.

The `settings.menu_order` preference stores all ten items, even disabled tools; re-enabling a hidden tool restores its previous position. The preference is automatically saved, included in Settings backup/restore (not in Quick Slots), and reset via Settings → Reset menus. Previous profiles/backup ZIPs without this preference continue using the default order. No automatic external access or files are involved.

Settings category and tool icons now use Pocket's own Pillow vector renderings, not system-font symbols. **Visible Tools is directly below Appearance** in the single-column Mini/Normal Settings and in the same Dashboard column.

## Verification

CI uses isolated synthetic profiles and mocked Office automation. Tests include consecutive Excel shortcut clicks while another Excel application is already active, EXCEL.EXE `/x` launching, fallback and failure cleanup, all original Settings controls and callbacks, category switching without changing saved preferences, Mini/Normal/Dashboard GUI smoke, and Windows portable EXE packaging. No corporate workbook data is bundled.
