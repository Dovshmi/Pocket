# Pocket v1.30.0 — Smart Templates and Extra Mini Quick Actions

**STABLE RELEASE · Windows 10/11 · Unsigned EXEs · Optional new features**

This is the **latest stable release**, superseding v1.29.1. It includes all previous Pocket tools and the major new Extra Mini and Commands upgrades.

## What is new

### Smart Command Templates (optional)
- Create and approve a template for an existing CLI command without changing its original text.
- Conservative suggestions handle familiar placeholder patterns, but you always review the suggested format.
- Simple template creator: original command, editable format, **Refresh fields** count, optional **Field options** for advanced validation.
- **Fill & copy** opens a dedicated form with a generated-command preview and visible **Copy command** button.
- No CLI is executed. Entered values are not saved in the command library or copied into Pocket's session Clipboard History.
- Existing command search, plain copying, editing, favorites, recent history, and **manual** backups continue to work.

### Extra Mini: 3 pages × 4 tiles
- **Twelve slots** over three pages in the same compact 322×256 launcher.
- Page dots, previous/next arrows and mouse-wheel paging; remembers the last page.
- Searchable picker for an enabled Pocket tool, specific saved note, exact command, approved Smart Template or saved shortcut.
- Optional direct copy of a specific **plain CLI command**; Smart Templates still require filling and confirmation.
- Rename tiles or pages, replace/remove tiles, and move or swap tiles between pages.
- Existing users' four original tiles migrate to page one in their saved order. Other pages start empty.
- Missing items, hidden menus and stale templates are disabled rather than silently redirecting.
- Extra Mini still restores the user's chosen Normal, Mini or Dashboard working layout.

## Download and installation

- **Pocket-Portable-v1.30.0.zip (recommended)**: Extract everything, then run `PocketDesk.exe`. Preserve the existing `data/` directory when upgrading from a portable installation.
- **Pocket-v1.30.0.exe**: Standalone one-file Windows EXE that uses Pocket's standard AppData storage location.
- **SHA256SUMS.txt**: checksums for both files.

**Before upgrading:** Close Pocket fully from the notification area; make a safe copy of your existing `data/` folder and personal `commands.json`. If running older and newer builds side by side, use separate portable directories and do not run both against the same data files.

## Compatibility and limits

- All seven established tools and three working modes remain available. Pocket stays local-first.
- Existing CLI commands remain **copy-only**; templates do not execute commands and never require an internet connection.
- One-time reminders and other existing controls retain their behavior.
- Windows/Linux unit and Tk GUI regression tests, Windows portable/standalone packaging, integrity and packaged-EXE launch checks run before publishing.
- **Known limitations:** Visual layout and drag-and-drop on different Windows DPI scales, native RTL note editing, and tray/hotkey behavior need real-device feedback. This beta is not code-signed, and your organization's device policy may block it.
- Report issues at https://github.com/Dovshmi/Pocket/issues and exclude sensitive user/network data from reports.

Earlier versions, including [Pocket v1.29.1](https://github.com/Dovshmi/Pocket/releases/tag/v1.29.1) and the [v1.30.0-beta.1 preview](https://github.com/Dovshmi/Pocket/releases/tag/v1.30.0-beta.1), remain available in the release history.
