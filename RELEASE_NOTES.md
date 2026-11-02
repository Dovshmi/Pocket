# Pocket v1.32.0 — Dashboard Workspace & Reliability

**Stable Windows release · Local-first · Unsigned EXE**

Pocket v1.32.0 builds on v1.31.0 with a cleaner source architecture, better recovery from damaged data, and redesigned wide Dashboard menus. **Normal, Mini and Extra Mini retain their established controls and layouts.**

## New in v1.32.0

### Dashboard: use the wide workspace
- **Commands:** larger 16-row reference list and editable command preview side by side, with quick search, vendor/category filters, favorites, Smart Templates and a draggable divider. Commands are copy-only; they are never executed.
- **Notes:** full-height writing editor, compact title and phone fields on the same row, and a dedicated notes sidebar. Native Windows Unicode editing, reminders, autosave and note actions remain available.
- **Shortcuts:** responsive cards displayed in multiple columns with instant search, Website/File/Folder filters, compact add/edit form, Open/Copy actions and drag-and-drop.
- **Settings:** balanced two-column arrangement of appearance and theme palettes, visible tool toggles, Extra Mini launcher, keyboard shortcuts and clipboard privacy. Settings still apply immediately and are stored locally.

### Data integrity and recovery
- Validate personal `data.json` before writing; use atomic file replacement with a rolling **previous valid snapshot** at `data-recovery.json`.
- On damaged data, preserve the original as `data-corrupt-*.json`, attempt recovery from the last good snapshot and display a warning. If an unsaved change cannot be written, Pocket shows an error and stays open instead of silently closing.
- Avoid rewriting identical data unnecessarily. Personal recovery files remain **local and unencrypted**; store your Pocket data folder securely.
- **CLI command-library backups remain manual-only**, via the explicit Backup button. The new data snapshot applies to `data.json`, not to the command library.

### Behind the scenes
- Group runtime code under the `pocket/` package, regression tests under `tests/`, historical scripts/screenshots under documentation.
- Separate reusable Notes operations from UI and coordinate recurring local clipboard, reminder, Notepad and editor tasks with cancellable timers.
- Remove two legacy workbook-derived command-library copies from the current repository tree; source and Windows builds use the approved **public example commands**. Earlier copies remain in Git history; this release does not rewrite history.
- No automatic network operations or new online requirements. Port checks and IEEE registry updates still run only when requested.

## Download

- **Pocket-Portable-v1.32.0.zip** — recommended; extract the entire folder, then run `PocketDesk.exe`. The portable data folder stays beside the application.
- **Pocket-v1.32.0.exe** — single-file Windows executable; user data is stored under Pocket's standard AppData location.
- **SHA256SUMS.txt** — SHA-256 checksums of both downloads.

The files are generated and published only after Windows unit tests, the full GUI smoke test, standalone EXE launch, ZIP integrity and personal-data exclusion checks succeed. Both EXEs are unsigned; Windows SmartScreen and corporate application restrictions may apply.

## Upgrade safely

1. Exit Pocket completely (including the system tray).
2. Back up your existing **portable `data/` folder** and your personal `commands.json` before upgrading.
3. Extract the new portable ZIP into a **fresh directory**, then copy your existing `data/` directory across. Do not merge the old and new `_internal/` folders.
4. Open only one version of Pocket at a time. If a data-recovery warning appears, retain the preserved `data-corrupt-*.json` file and review your backup before further editing.

Clipboard history remains session-only. The published binaries do not include private notes, personal commands, working backups or recovery snapshots. Smart Templates stay copy-only.

[Previous stable releases](https://github.com/Dovshmi/Pocket/releases) remain accessible.
