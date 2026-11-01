# Pocket v1.31.0 — Interface & Notes Reliability Update

**STABLE RELEASE · Windows 10/11 · Unsigned Windows EXEs · Local-first**

This release builds on v1.30.0 Smart Command Templates and Extra Mini, with redesigned navigation, improved workspace density, more flexible launcher pages, consistent icons, and improved note-editor focus.

## What's new

### Extra Mini launcher
- **Pages grow with your saved actions:** the first four actions need one dot; a fifth action opens a second page, and further groups of four appear only when needed. No forced three-page display.
- A friendlier, searchable quick-action picker with clickable categories and double-click selection.
- The footer **+ Add** control is shown **only in Edit mode** and disappears when you click **Done** or leave editing.
- Existing note, command, Smart Template, shortcut, and tool references remain available; page names and positions stay stored locally. No CLI is executed.

### Normal working layout
- Icon-and-name navigation matching Pocket's Mini visual language, with a **More** overflow menu when needed; the selected tool remains visible and Settings is always accessible.
- Better-balanced title bar, action headers, editors, spacing, and information density.
- Notes, Shortcuts, MAC Lookup, and Subnet Calculator fit more content in the same 480×850 window. Subnet facts are presented in two columns.

### Notes, icons, and scrolling
- Improved **single-click focus transitions** between the Notes body, title, phone number, picker, and background in Mini and Normal, including the native Windows RichEdit editor.
- **Mini note arrow controls and keyboard paging are preserved.** Dashboard's note workflow is preserved.
- Locally drawn tool icons replace glyphs that could appear as a question mark on some Windows font configurations.
- Shortcuts uses Pocket's themed scrollbar in Normal and Dashboard; Mini's existing scrollbar behavior is unchanged.
- Removed the redundant Search control from the Normal/Mini title bars; the global **Ctrl+K** search shortcut remains available.

## Downloads

- **Pocket-Portable-v1.31.0.zip** (recommended): extract the entire ZIP and run `PocketDesk.exe`. Portable data stays in the adjacent `data/` folder.
- **Pocket-v1.31.0.exe**: one-file Windows executable; application data lives under the standard AppData location.
- **SHA256SUMS.txt**: SHA-256 checksums for the two Windows downloads.

Both executable builds are unsigned. Your PC's Windows SmartScreen or workplace application controls may restrict them.

## Upgrade safely

1. Exit Pocket completely from the Windows tray.
2. **Back up** your existing portable `data/` folder and any personal `commands.json` before changing installations.
3. For portable installations, extract the new build to a **clean folder** and move your existing `data/` folder into it. Do not mix old and new `_internal/` directories.
4. Don't run two Pocket versions simultaneously against the same data folder.

Portable archives bundle only the **public example command library**, never private notes, saved commands, clipboard history, or working backups. Smart Templates remain copy-only; template inputs are not saved.

## Validation and compatibility

- Release workflow runs Python regression tests, real Windows Tk UI smoke tests, portable and standalone Windows builds, archive-integrity and personal-data-exclusion checks, and an isolated standalone executable launch test **before publishing**.
- No new online dependency, authentication, or CLI execution behavior is introduced.
- As with earlier unsigned releases, native RTL text editing and different Windows display/DPI configurations should also be checked on real devices.

Previous versions remain available under [GitHub Releases](https://github.com/Dovshmi/Pocket/releases). Please report issues without including internal network data, customer information, or personal notes.
