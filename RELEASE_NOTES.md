# Pocket v1.36.0 — Native Windows Inputs & Mini Improvements

**Stable Version 1.36 · Windows 10/11 · Portable ZIP + standalone EXE**

This release combines the changes developed and verified in the Pocket `fix/input-editing-smart-mac-port-order` branch. All previous v1.35.1 tools, layouts and local data formats remain supported.

## What's new

- **Native Windows editing:** Single-line fields and selected multiline editors use Win32 EDIT/RichEdit with normal Ctrl+A, Ctrl+C, Ctrl+X, Ctrl+V, Ctrl+Z shortcuts, Pocket's compact editing menu, corrected text colors and compact field alignment. The specialist Notes editor keeps its own rich-text behavior.
- **MAC Lookup improvements:** Recognizes MAC addresses in pasted switch/CLI tables. Large MAC and CLI command text fields can scroll using the mouse wheel without adding visible scrollbars.
- **Port Checker:** Reachable/open ports are listed before closed or timed-out entries to make results easier to scan.
- **Mini Commands:** Machine selection on the left and category on the right, on one row; the CLI search fills the row below.
- **Mini Notes & CLI dropdowns:** Normal click-to-select lists are retained. Experimental type-to-search was deliberately removed; text selection highlighting clears once the dropdown closes, while the chosen value remains visible.
- **Clipboard Manager:** Pinned text history appears at the top of the list, with original order preserved within pinned/unpinned groups.
- **Local-first:** Editor and clipboard improvements are fully local. DashDash checks still run only when explicitly requested.

## Verification

Windows and Linux unit tests and GUI integration tests cover Notes, MAC Lookup, Commands, editing shortcuts, clipboard pin order, Mini layout and dropdown selection. The Windows release workflow additionally compiles and tests a self-contained portable package and standalone executable, validates the extracted native dependencies, checks ZIP integrity and SHA-256 checksums, and exercises packaged startup.

## Release downloads

- **Pocket-Portable-v1.36.0.zip** — recommended for work PCs. Contains `Pocket-Portable/PocketDesk.exe`, `_internal/`, integrity manifest and `Verify-Pocket.ps1`.
- **Pocket-v1.36.0.exe** — standalone Windows executable, with the same features.
- **SHA256SUMS.txt** — hashes of both release assets.

Public packages exclude personal notes, profiles, backups, credentials, clipboard history and private `commands.json` files. Release executables are **not code-signed**.

## Upgrade safely

1. Exit Pocket completely, including its system-tray process.
2. Back up your data. Portable installations store settings and notes under `Pocket-Portable/data/`; the standalone executable uses `%APPDATA%\\PocketDesk\\`.
3. Extract v1.36.0 into a **new folder** and do not combine old/new `_internal/` runtime files. Move only your existing `data/` folder into the new portable installation when ready.
4. Launch Pocket and verify your saved Notes, Commands, Clipboard preferences, theme and Mini/Normal/Dashboard mode.

The previous [v1.35.1 release](https://github.com/Dovshmi/Pocket/releases/tag/v1.35.1) remains available.
