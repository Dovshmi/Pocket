# Pocket v1.35.1 — Clipboard Alignment & Consistent Layout

**Stable Windows patch release · Windows 10/11 · Portable ZIP + standalone EXE**

This patch is built from the updated `main` branch, including the fixes merged in [PR #22](https://github.com/Dovshmi/Pocket/pull/22). It contains all v1.35.0 features.

## Fixed

- **Clipboard text alignment:** Removed an artificial three-space prefix from unpinned history entries. Clipboard rows now start at the normal Listbox text inset; pinned entries still show their star.
- **Clipboard border:** Replaced the Windows-native, thick bright focus border with the same subtle **1px themed border** used elsewhere in Pocket, including a themed focus highlight.
- **Dashboard navigation:** Restores the original tool-content parent when switching between scrollable and non-scrollable menus. This prevents progressively nested scroll frames and unintended horizontal offset or shrinkage.
- **Consistent menus:** Added automated GUI checks for the horizontal content gutter and correct scroll-parent ownership across **Normal, Mini and Dashboard**, visiting every menu.

## Unchanged from v1.35.0

- Modern Settings, Mini default for new profiles, Ushpelo starter shortcuts, and saved last-active menu.
- Clipboard image history capacity **10, 15, 20, 25, 30** (20 by default), kept only in RAM.
- Offline EN/HE keyboard-layout conversion, fixed Notes editor focus and hidden editor scrollbar, Extra Mini control, improved Command Helper and author/version credits.
- Local-first behavior. Network checks occur only when initiated by the user. Existing user settings, notes, shortcuts and clipboard privacy rules are unchanged.

## Verified release contents

The publishing workflow runs Windows unit and full GUI checks, builds both packages, verifies the extracted ZIP's dependencies and internal manifest, tests the standalone EXE startup, and creates SHA-256 checksums before publishing.

- **Pocket-Portable-v1.35.1.zip** — extracted portable Windows app, with `PocketDesk.exe`, `_internal/`, integrity manifest and verification script.
- **Pocket-v1.35.1.exe** — standalone Windows executable.
- **SHA256SUMS.txt** — SHA-256 checksums for the ZIP and EXE.

Public packages exclude user profiles, private `commands.json`, saved notes, credentials, and clipboard history. Binaries are not code-signed.

## Upgrade without losing your data

1. Exit Pocket completely from the Windows system tray.
2. Back up your current user data: portable installations keep it under `Pocket-Portable/data/`; standalone uses `%APPDATA%\\PocketDesk/`.
3. For Portable, extract v1.35.1 into a **new folder** and copy your previous `data/` folder into it. Do **not** combine old and new `_internal/` directories.
4. Open Pocket again. Your selected mode, theme, notes, last-used tool, TCP preferences and shortcut folders are preserved.

The previous [v1.35.0 release](https://github.com/Dovshmi/Pocket/releases/tag/v1.35.0) remains available separately.
