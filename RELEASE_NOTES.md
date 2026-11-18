# Pocket v1.39.3 — Separate Automatic Copy and Paste Controls

**Stable patch release · Windows 10 / Windows 11 · Portable ZIP and standalone EXE**

Quick Slots now have two separate preferences under **Settings → Clipboard & privacy**:

- **Quick Slot save behavior:** **Auto Copy Selection** (legacy default) issues Ctrl+C and saves the selected text, falling back to existing clipboard text when the app offers no new selection. **Use Current Clipboard** reads previously copied text without simulating Ctrl+C; copy text yourself first.
- **Quick Slot paste behavior:** **Auto Paste** (legacy default) inserts the saved slot immediately, or **Copy to Clipboard** places it in the Windows clipboard for a manual Ctrl+V.
- **Independent selection:** any combination is supported, saved across restarts, with no change to existing hotkeys or stored slots.

For programs where automatic Unicode paste of Hebrew is rejected or renders question marks, choose Copy to Clipboard for Paste and press regular Ctrl+V in that program. Windows does not guarantee injected keystrokes behave like genuine user paste in all applications; this version offers explicit control rather than making unsupported guarantees.

The Quick Slot settings are still excluded from exported backups. Operations are local and offline.

**Upgrade:** Fully quit Pocket, extract the updated portable ZIP into a new directory, and copy your old `data/` folder across. Do not mix older `_internal/` runtime files.

[Detailed release notes](docs/releases/v1.39.3.md) · [Quick Slots documentation](docs/QUICK_SLOTS.md)

---

# Pocket v1.39.2 — Hebrew & Multilingual Quick Slots Paste Fix

**Stable patch release · Windows 10 / Windows 11 · Portable ZIP + standalone EXE**

Pocket 1.39.2 fixes Hebrew text becoming question marks when Quick Slots Auto Paste targets some Windows applications.

- **ASCII-only slots:** Keep the reliable clipboard-independent Unicode keystroke insertion from 1.39.1.
- **Hebrew and other non-ASCII slots:** Use native Windows `CF_UNICODETEXT` and standard `Ctrl+V`, avoiding target applications interpreting injected characters as `?`.
- **Clipboard behavior:** After automatically pasting non-ASCII text, the slot stays in your clipboard. This is intentional: no attempt is made to restore the old clipboard through Windows OLE, which failed with `CloseClipboard Failed` on some workstations.
- **Compatibility:** Manual **Copy to Clipboard** mode, existing slots, shortcuts, Notes, settings, CLI and network tools are unaffected. All actions are offline.

### Upgrade

Close Pocket fully, back up your portable `data/` directory, extract the 1.39.2 Portable ZIP into a **new folder**, and copy your old `data/` into it. Never mix old and new `_internal/` runtime files.

Windows CI tests both paste paths with real Hebrew text, packages a portable ZIP and standalone EXE, verifies ZIP privacy/integrity and publishes `SHA256SUMS.txt`. Restricted workplace applications still need an on-device check.

[Quick Slots guide](docs/QUICK_SLOTS.md) · [Detailed patch notes](docs/releases/v1.39.2.md)

---

# Pocket v1.39.1 — Quick Slots Clipboard Fix

**Stable · Windows 10 / Windows 11 · Portable ZIP + standalone EXE**

Pocket v1.39.1 fixes Quick Slots auto-paste failures involving Windows OLE clipboard snapshot/restore errors, such as the `CloseClipboard Failed` notification, and adds a persistent **Copy to Clipboard** mode.

- **Auto Paste (default):** Types the selected slot through native Unicode input, without opening or modifying the existing Windows clipboard. No OLE snapshot, temporary replacement or restoration is needed.
- **Copy to Clipboard:** In **Settings → Clipboard & privacy → Quick Slot paste behavior**, choose Copy to Clipboard. Press the Quick Slot paste hotkey, then your ordinary `Ctrl+V`; the slot becomes the current clipboard contents and is intentionally not restored.
- **Safety:** Auto Paste checks the original foreground window before and during typing and does not manipulate existing clipboard formats. There is no risk of an OLE restore failure overwriting another app's clipboard. Existing Quick Slots, shortcuts and locally saved data stay intact.
- **Offline:** No network or remote API is used for either paste mode.

Automatic Unicode injection can be blocked by elevated, remote, or specialized applications; Copy to Clipboard provides a manual alternative in those cases.

## Official Windows packages

- [Portable ZIP](https://github.com/Dovshmi/Pocket/releases/download/v1.39.1/Pocket-Portable-v1.39.1.zip)
- [Standalone EXE](https://github.com/Dovshmi/Pocket/releases/download/v1.39.1/Pocket-v1.39.1.exe)
- [SHA-256 checksums](https://github.com/Dovshmi/Pocket/releases/download/v1.39.1/SHA256SUMS.txt)

Builds are unsigned. Completely close Pocket before updating; install into a fresh folder, preserve only your local `data/` directory for portable upgrades, and never mix `_internal/` DLLs from old and new versions.

---

# Pocket v1.39.0 — Quick Slots, Portable Backups & Smarter Settings

**Stable release · Windows 10 / Windows 11 · Portable ZIP + standalone EXE**

Pocket v1.39.0 brings offline-first profile backup and restore, direct clipboard Quick Slots, live keyboard shortcut recording, improved Notes and smarter Settings. It preserves the Windows tray workflow, the existing network/CLI utilities, and compatibility with earlier Pocket profile data.

## What's new

### 1. Selective Backup & Restore

Under **Settings → Backup & Restore**:

- **Create Backup** writes a single portable ZIP containing *only* the selected categories: **Notes & reminders**, **Links & folders**, **CLI commands and templates**, **Settings**, and optionally **Clipboard DATABASE text history** and/or **Clipboard DATABASE screenshots**.
- Categories with no exportable content are disabled. Available categories start selected and can be individually unchecked.
- **Restore Backup** opens an existing Pocket ZIP. Missing or empty categories are greyed out; importable categories are selected automatically. The scrollable preview displays additions, unchanged entries and conflicts. The preview supports mouse-wheel scrolling without a visible scrollbar.
- **Merge** adds missing IDs and preserves local records when IDs conflict. **Replace** overwrites *only* selected categories. Settings values are applied when Settings is selected, even in Merge.
- Before writing restored data, Pocket saves a **pre-restore recovery ZIP** inside the local `backups/` folder. The backup ZIP is validated for version, structure, integrity, size and unsafe paths.
- The import closes Pocket after a successful restore; reopen to apply updated settings and shortcuts.

**Quick Slot values and Quick Slot shortcut preferences are always excluded** from portable backups, including when Settings is selected. RAM-only clipboard history is not exportable. Backups are local and **unencrypted** and may include sensitive CLI commands, note contents and clipboard records. Review them before transfer; no online synchronization or automatic periodic backup is performed. Link targets to local files/folders are references, not copied file content.

Read [Backup & Restore documentation](https://github.com/Dovshmi/Pocket/blob/main/docs/BACKUP_RESTORE.md).

### 2. Direct Quick Slots on the physical Numpad

With **Num Lock ON**:

| Action | Default global shortcut |
| --- | --- |
| Save highlighted text, or existing Windows clipboard text if nothing is selected, into slot N | `Ctrl+Win+Numpad1–9` |
| Paste text from slot N into the focused application | `Ctrl+Alt+Numpad1–9` |

- Dedicated *Save/Copy* and *Paste* modifier prefixes can be configured independently; the Numpad1–9 suffix is fixed.
- Copying highlighted text performs ordinary Ctrl+C and stores the copied text in the numbered slot. Without highlighted text, the current clipboard text remains the fallback.
- Paste uses the selected slot while preserving the user's clipboard. Overwriting a nonempty slot requires confirmation.
- All Quick Slots stay local and remain excluded from the portable backup.

Read [Quick Slots documentation](https://github.com/Dovshmi/Pocket/blob/main/docs/QUICK_SLOTS.md).

### 3. Live shortcut recording and Default Settings

- **Record Shortcut** captures a popup/Translate keyboard chord locally in Settings, alongside the existing manual modifier/key picker.
- Quick Slot shortcut recording captures the modifier keys plus a fixed Numpad1–9 key. Ctrl, Ctrl+Alt, Ctrl+Win and Ctrl+Alt+Win are supported; save and paste cannot share a prefix.
- **Default Settings** can reset chosen preference groups (Appearance, Menus, Keyboard, Clipboard preferences and Network) without deleting Notes, Links, CLI data, Clipboard history or saved Quick Slot values.
- The Settings footer now displays **v1.39.0**.

### 4. Notes and UI refinements

- Updates the untouched first factory Note to title **הבאכש מתקרר** and body **תקלה באיזור בוכרה, הכל תקין אבל החינקלי כבר קר!!!!!**. User-edited notes are preserved.
- Keeps Normal, Mini, Dashboard and Extra Mini layouts and the existing clipboard, subnet, TCP port, MAC vendor, CLI and shortcut tools.
- Restore previews are more readable on compact Windows screens; optional selections are explicit.

## Download assets

| Asset | Purpose |
| --- | --- |
| **Pocket-Portable-v1.39.0.zip** | Recommended for work PCs: extracted `Pocket-Portable/PocketDesk.exe`, bundled Python/native dependencies, integrity manifest and `Verify-Pocket.ps1` |
| **Pocket-v1.39.0.exe** | Standalone Windows executable |
| **SHA256SUMS.txt** | SHA-256 checksums for both Windows packages |

The distributed binaries include only the sanitized example CLI library. **No personal Notes, `data.json`, private `commands.json`, vendor cache, Clipboard DATABASE, passwords or local backup files are bundled.** Both Windows binaries are unsigned; follow workplace application-control policy rather than disabling security checks.

## Upgrade from v1.38.0 or earlier

1. Exit Pocket completely through the tray icon (**Exit**).
2. Back up the current profile. Portable installations use `Pocket-Portable/data/` beside the EXE; standalone installations use `%APPDATA%\PocketDesk\`.
3. **Portable:** Extract the *entire* new ZIP into a **new local folder**; do not mix old and new `_internal/` files. Copy only your existing personal `data/` directory into the new portable directory. Alternatively, use the new selective ZIP Backup/Restore for a future transfer once v1.39.0 is running.
4. **Standalone:** Replace the EXE; your `%APPDATA%\PocketDesk\` profile remains separate from the executable.
5. Reopen, confirm Notes/Links/CLI and shortcut preferences, and test keyboard shortcuts against the programs you use. Verify optional Clipboard DATABASE retention settings before exporting history.

Internet connectivity is not required for Notes, local CLI lookup, subnet calculation, clipboard functions or backup/restore. Optional DashDash network checks and explicit external link opening are the only network-dependent workflows.

## Verification

The Windows release pipeline compiles and tests Pocket, runs GUI integration checks, builds both packages, validates the sanitized contents of the portable archive and the native Windows runtime, exercises packaged GUI startup for portable and standalone applications, and writes SHA-256 checksums before publishing.

Earlier history: [v1.38.0](https://github.com/Dovshmi/Pocket/releases/tag/v1.38.0) · [v1.36.0](https://github.com/Dovshmi/Pocket/releases/tag/v1.36.0). Full historical notes: [RELEASE_NOTES.md](https://github.com/Dovshmi/Pocket/blob/main/RELEASE_NOTES.md).

---

# Pocket v1.38.0 — Clipboard Selection Counter & History Options

**Stable release v1.38.0 · Windows 10/11 · Portable ZIP + standalone EXE**

This release includes the requested v1.38 Clipboard refinements and integrates the v1.37 development improvements. Existing Pocket v1.36 settings and local data remain supported.

### Clipboard refinements in v1.38.0

- **Text selection indicator:** The existing grey Clipboard Text status displays **selected position / displayed entries**, matching the Images selection indicator. The count follows mouse, keyboard, pinning and text-selection changes; it does not add or move UI controls. Mini omits redundant date/storage text from this narrow status line to prevent clipping.
- **RAM screenshot capacity:** Choice list restored to **10 / 15 / 20 / 25 / 30** images, with **20 as the factory default**. Existing saved preferences of 15 and 25 remain intact; previously allowed 40–100 are safely capped to 30.
- **DATABASE text shown:** Independent options **100 / 300 / 500 / 800 / 1000 / 1200 / 1500** entries, default **100**. Older 10–100 values migrate to 100, and any intermediate saved count rounds up to the nearest supported option. Saved daily TXT history is not changed or deleted by this migration.
- **DATABASE screenshots shown:** Retains its independent 10–100 in steps of ten (30 default).
- **Settings layout unchanged:** The existing two-column dropdown grid, mouse-wheel behavior, clipboard content area, date selector, and text/image positions remain in place.

### Functionality included from the previous v1.37 development work

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

- **Storage dropdown:** A compact Storage (RAM / DATABASE) dropdown shares a row with the date selector, freeing space in Mini. RAM remains the default with session-only text and configurable **10–30** screenshot slots (20 default) in v1.38. DATABASE is opt-in and preserves copied content across restarts.
- **Append-only daily text journal:** One UTF-8 TXT file per date, named with its creation timestamp and expiry or `to_saved`, contains structured JSON lines. New copies append efficiently; pin/delete operations atomically rewrite the selected day without dropping entries on other pages.
- **One screenshot folder:** `ClipboardDatabase/ClipboardScreenshots/` contains all date-prefixed PNG files (no per-day subfolders). Migration safely moves recognized old daily-folder PNGs without overwriting conflicts. Full-resolution PNG data is loaded only for thumbnails being drawn or for Copy/Preview; the on-screen item count does not limit disk storage.
- **Compact history layout:** Browse prior dates through Storage/Date selectors and scroll the text list or image gallery to load older items automatically—no redundant Prev/Next navigation row. Clipboard & privacy uses a short **2×2 dropdown grid** for RAM images, DB images, DB text and 7–30-day cleanup. Only these four selectors intercept the mouse wheel and scroll the Settings page instead of changing values. DATABASE screenshot batches remain **10–100 items**; text batches are **100–1500**.
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

### Release downloads

- **Pocket-Portable-v1.38.0.zip** — recommended for work PCs; includes `Pocket-Portable/PocketDesk.exe`, bundled native runtime, integrity manifest and `Verify-Pocket.ps1`.
- **Pocket-v1.38.0.exe** — standalone Windows executable.
- **SHA256SUMS.txt** — SHA-256 checksums of both packages.

The public packages contain sanitized example commands only. They exclude private notes, passwords, local profiles, clipboard history, backups and personal command files. Executables are **not code-signed**.

### Upgrade safely

1. Close Pocket completely, including its tray process, and back up your existing data.
2. Extract the v1.38.0 portable ZIP into a **new folder**. Do not mix old and new `_internal/` runtime files.
3. For an existing portable installation, copy only your saved `data/` folder to the new portable installation. For a standalone installation, keep your existing `%APPDATA%\\PocketDesk\\` profile.
4. Check Notes, Commands, Clipboard settings and the preferred UI mode. Database history is plaintext; review your workplace storage policy before enabling it.

The previous [v1.36.0 release](https://github.com/Dovshmi/Pocket/releases/tag/v1.36.0) remains available.

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
