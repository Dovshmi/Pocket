# Pocket — Backup & Restore and keyboard recording (development)

These features are implemented on the development branch
`feature/backup-restore-record-hotkeys`; the currently published stable
v1.38 download in the README has not been replaced.

## Create Backup

1. Open **Settings → Backup & Restore → Create Backup**.
2. Choose only the data to include (by default: Notes, Links, CLI, Settings).
3. Optionally include **Clipboard DATABASE text** and/or **saved screenshots**.
4. Click **Save ZIP**, choose a file path, and transfer the resulting ZIP to
   the other Windows computer using your approved method.

A backup is **only** created when you press Save ZIP. Changing an ordinary note
or setting does not automatically create a new portable backup.

| Category | Included | Notes |
| --- | --- | --- |
| Notes | Titles, text, phone fields, creation dates, reminder metadata, note IDs and pin state | User edits and IDs are preserved |
| Links | URL/file/folder targets, labels, folder grouping/order | Local file paths might not exist on the new PC; files themselves are not copied |
| CLI | The writable `commands.json` library (including template metadata), machine favorites, recent items, custom records | A separate Commands-only backup feature also exists |
| Settings | Appearance, layouts, menu visibility, network proxy and normal Popup/Translate hotkeys | Machine-specific window coordinates and network credentials are not included |
| Clipboard DATABASE text | Saved daily journal history, **opt in** | RAM-only history is not exportable after the session |
| Clipboard DATABASE screenshots | Local saved PNGs, **opt in** | RAM-only screenshots are not exported |
| **Quick Slots** | **Never included** | Slot contents, enabled state and the Numpad shortcut preferences stay local |

**Backup files are NOT encrypted.** CLI records, Notes and optional clipboard
history can contain credentials or other sensitive information. Inspect them
and use approved storage/transfer methods, particularly on a managed work PC.
Pocket performs no cloud upload, network synchronization or scheduled backup.

## Restore Backup on another PC

1. Install or extract the same (or compatible newer) Pocket build and open
   **Settings → Backup & Restore → Restore Backup**.
2. Choose a Pocket ZIP archive. The file is checked for expected version,
   category structure, member size, safe paths and SHA-256 checksums.
3. Choose only the categories to import, and select a strategy:
   - **Merge** (default): add missing IDs without deleting local content.
     When an ID already exists with different content, the local entry wins.
     Preview shows the number of conflicts.
   - **Replace**: overwrite only the selected categories. Unselected
     categories are left unchanged.
4. Review the preview and confirm. Pocket saves a
   `backups/Pocket-before-restore-*.zip` rollback archive **before** making
   changes.
5. Pocket closes when the restore completes. **Reopen it** to load fresh
   settings, clipboard data and Windows keyboard registrations.

**Settings are values rather than additive records:** selecting Settings during
either Merge or Replace applies backed-up settings values. Quick Slot contents
and preferences remain untouched. When importing CLI in Merge, commands
with differing existing IDs stay local. In Replace, the imported command
document becomes the active library.

The restore validates files before writing. Files in different categories
cannot be committed with a single atomic filesystem transaction. If a storage
failure occurs partway through a restore, use the pre-restore ZIP to recover.
Never restore a ZIP whose origin you don't trust.

## Reset to Default Settings

Settings → **Default Settings → Reset…** lets you select groups:

- Appearance & layouts
- Visible menus & launcher
- Keyboard & hotkeys (including **Quick Slot shortcut settings**, but not the
  stored Quick Slot text)
- Clipboard preferences (not saved text/images/history files)
- Network connection preferences

Only the selected preferences return to factory values. Notes, Links, CLI
content, Clipboard DATABASE and Quick Slot data are preserved. Pocket closes
after a confirmed reset; reopen it to re-register hotkeys and redraw the UI.

## Record Shortcut

Settings → Keyboard → Edit supports both the existing modifier/key picker
and **Record Shortcut**. With the recorder active, press the desired key
combination, review the captured shortcut and choose **Save shortcut**. The
Windows registration step detects unavailable shortcuts and keeps the previous
one when there is a conflict.

For Quick Slots, separate **Record** controls accept modifiers plus any
**Numpad1–9** key while Num Lock is on. The number is a fixed suffix;
only the modifier prefix changes. Ctrl, Ctrl+Alt, Ctrl+Win and
Ctrl+Alt+Win are supported (no Shift). Paste and Save cannot use the same
modifier prefix.

Recording is a temporary UI interaction, **not a permanent keylogger**.
Windows may intercept certain Win-key combinations before a Tk window sees
them; the existing manual dropdown remains available as a fallback.
