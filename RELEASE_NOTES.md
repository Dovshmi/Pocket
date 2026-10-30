# Pocket v1.28 — Portable Windows Release

**Windows 10/11 · Local-first · No Python installation required**

This release adds the portable distribution and the final note-editing fixes to Pocket v1.27.

## Highlights

- **Portable Windows ZIP:** extract the whole folder and run `PocketDesk.exe`; no installer or Python required on the destination PC.
- **Local-first storage:** notes, reminders, shortcuts, window positions, settings, generated icons, MAC vendor cache, commands and Notepad working files live alongside the app in `data/`.
- **Single-instance protection:** running Pocket twice opens the first instance instead of adding duplicate tray icons or risking competing writes.
- **Notes focus fix:** in Normal Mode, clicking Title, Phone, or outside the note editor releases native Windows RichEdit focus. Mini Mode remains unchanged.
- **Existing tools:** Notes, Shortcuts, TCP Ports, MAC Lookup, Commands, Subnet, Clipboard, Notifications, RTL/LTR, and Normal/Mini Mode.

## Install / update

1. Download `Pocket-Portable-v1.28.zip` from the release assets.
2. Extract **all** files to a writable folder (not inside Program Files or the ZIP).
3. Double-click `Pocket-Portable/PocketDesk.exe`. No Python installation is necessary.
4. To update an existing Pocket Portable folder, **exit Pocket completely**, preserve its `data/` folder, then replace only application files (`PocketDesk.exe`, `_internal/`, marker/README) with the new version. Do not overwrite `data/`.

The archive includes only safe public **example CLI commands**, not your own command library, notes, or backups. To migrate from a non-portable installation, close Pocket first and copy your files manually after reviewing them. The active data folder of a standard source installation is `%APPDATA%\\PocketDesk`.

## Notes

- Clipboard history intentionally exists in memory only and is not transferred.
- Shortcut targets pointing to local files/folders need to exist on the destination computer.
- The EXE is **unsigned**; employer policies/SmartScreen may limit execution. Do not bypass organizational security controls.
- Internet access is not required for ordinary notes/commands/subnet lookups. Network operations use internet/network access only when explicitly invoked.
- The included ZIP and SHA256 checksum are generated automatically on a Windows GitHub Actions runner; automated tests passed on the previous development branch. Real-world device compatibility is not guaranteed.
