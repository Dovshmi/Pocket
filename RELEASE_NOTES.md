# Pocket v1.37.0 — Clipboard Database & Translate Controls (unreleased development)

**Branch:** feature/pocket-next-updates · **Stable release remains v1.36.0**.

This upcoming update groups the requested improvements together. It is not a published Windows release or a change to main.

### Notes and Notepad sync

- Newly created Notes are appended and selected at the last position in the Notes picker.
- A Note's Title matches the TXT working filename (without its .txt extension), including Windows-style numbered duplicates: Router, Router (1), Router (2).
- Renaming the Title also renames its TXT file after typing settles; locks and conflicts are handled without silently overwriting a neighboring note.
- Previous opaque Notepad files are migrated non-destructively.

### Two explicit internet connection modes

- **Use Windows Proxy: ON by default** under Settings. DashDash MAC and TCP requests continue using the existing native Windows WinHTTP PAC resolution and WinINet HTTPS POST stack, unchanged.
- **OFF:** DashDash requests use direct HTTPS with proxy discovery explicitly disabled for those requests.
- **Update IEEE DB:** uses native WinINet HTTPS GET in both modes. With Windows Proxy ON, it resolves the existing Windows PAC settings; with OFF, it uses WinINet's explicit **direct** mode and the Windows certificate trust store instead of Python TLS. This addresses Python's `CERTIFICATE_VERIFY_FAILED` on machines where Windows trusts the issuer. Untrusted certificates still fail; no TLS checks are disabled. Official IEEE URL restrictions, size limits, validation and atomic cache replacement remain enforced.
- No automatic fallback between corporate and direct modes; local checks continue to work offline. The setting is persisted per Pocket profile.

### Keyboard layout conversion

- Factory keyboard repair hotkey changes from **Ctrl+Alt+F9** to **Ctrl+Alt+V**; unchanged former factory profiles are migrated.
- Settings now offers a native dropdown for **Mark | Clipboard** selection, with **Mark by default** for new profiles. Clipboard mode preserves the previous behavior: convert existing clipboard text and leave it ready to paste.
- Mark mode reads a *freshly copied selection* from the active Windows application and applies the same offline EN/HE physical-keyboard mapping before automatically pasting over the selection.
- The Mark workflow checks focus/clipboard sequence changes, does not paste old clipboard text when nothing is selected, and attempts to restore all original clipboard formats using Windows OLE clipboard preservation. Mark does not work in every application; test in your editors before using on important unsaved text. No text is transmitted to the network.

### Clipboard RAM / local DATABASE (new in 1.37)

- **Storage dropdown:** A compact Storage (RAM / DATABASE) dropdown shares a row with the date selector, freeing space in Mini. RAM remains the default with session-only text and configurable **10–100** screenshot slots (20 default). DATABASE is opt-in and preserves copied content across restarts.
- **Append-only daily text journal:** One UTF-8 TXT file per date, named with its creation timestamp and expiry or `to_saved`, contains structured JSON lines. New copies append efficiently; pin/delete operations atomically rewrite the selected day without dropping entries on other pages.
- **One screenshot folder:** `ClipboardDatabase/ClipboardScreenshots/` contains all date-prefixed PNG files (no per-day subfolders). Migration safely moves recognized old daily-folder PNGs without overwriting conflicts. Full-resolution PNG data is loaded only for thumbnails being drawn or for Copy/Preview; the on-screen item count does not limit disk storage.
- **Compact history layout:** Browse prior dates through Storage/Date selectors and scroll the text list or image gallery to load older items automatically—no redundant Prev/Next navigation row. Clipboard & privacy uses a short **2×2 dropdown grid** for RAM images, DB images, DB text and 7–30-day cleanup. Only these four selectors intercept the mouse wheel and scroll the Settings page instead of changing values. Display limits remain **10–100 items**.
- **Optional cleanup:** Under **Clipboard & privacy**, auto-delete is **OFF by default** (history is retained until manually deleted). An explicit dropdown choice of **7 through 30 calendar days, in one-day increments**, deletes expired text and screenshots. Text filename expiry labels update accordingly; the former 1–5-day setting does not silently enable deletion.
- **Safe defaults:** Database history is never exported to DashDash or included in the app's release ZIP. RAM and DATABASE stores remain separate when switching; only bounded pages are displayed in RAM. The local Database is **plaintext**, and sensitive-text filtering cannot guarantee secrets/screenshots are excluded; enable persistent history only where local/workplace policy permits it.

### Translate keyboard repair preferences

- All controls are now grouped under **Settings → Clipboard & privacy**, beside image capacity and retention.
- **Enable Translate shortcut** is ON by default but can be toggled OFF, unregistering the global Windows hotkey without changing Pocket's popup shortcut.
- The default for a new profile is **Mark** mode with `Ctrl+Alt+V`. Clipboard mode remains selectable and works as before. Existing manually saved mode preferences are retained.
- Mark requires text selection in the original foreground application; it does not use the internet.

See [Clipboard Database documentation](docs/CLIPBOARD_DATABASE.md) for folder structure, retention semantics, and the privacy warning.

### Verification and availability

GitHub Actions exercises the unit suite, GUI smoke tests on Windows/Linux, the release-Python GUI smoke check, and a Windows portable build test. Live corporate PAC/IEEE authentication and actual third-party foreground text replacement must also be verified on the target Windows machine.

Development snapshots are available from the branch CI artifacts. Do not substitute them for the published v1.36.0 release until tested.

---

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
