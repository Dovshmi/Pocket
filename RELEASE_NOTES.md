# Pocket v1.29 — Modern Windows Desktop

**Windows 10/11 · Free and open source · No Python required**

This release brings the redesigned Pocket interface to the public stable branch.

## What's new

- **Three working layouts:** Normal, Mini and the wide Dashboard.
- **Optional Extra Mini:** 322 × 256 launcher with four customizable tiles. Minimize into it from any working mode and return to the same mode when opening a tool.
- **Modern Settings and controls:** theme-aware, keyboard-accessible actions, improved cards, inputs and tables.
- **Quick Search:** Ctrl+K searches notes, tool menus, saved shortcuts and CLI reference commands locally. Ctrl+F continues to focus Commands search inside Commands.
- **Clipboard privacy:** Pause/Resume capture and optional heuristic filtering for recognized passwords, keys and tokens. Clipboard history is never stored on disk.
- **All existing tools:** notes/reminders, shortcuts, TCP checks, MAC vendors, CLI commands, subnet calculator and clipboard history. CLI commands remain copy-only; manual command backups remain manual.

## Downloads

- **Pocket-Portable-v1.29.zip (recommended):** extract the entire folder to a writable location and run `PocketDesk.exe`. A `data/` folder beside the executable stores portable settings, commands and notes.
- **Pocket-v1.29.exe:** standalone Windows executable; no separate installation of Python or extracting a ZIP. This uses the regular local app-data location (not portable folder mode).
- **SHA256SUMS.txt:** checksums for both downloads.

## Update without losing notes

Exit Pocket completely from the tray before updating. For portable installations, keep your existing `data/` folder and replace only the program files with those from the new ZIP. Back up your `data/` directory before replacing application files. Do not merge an old `_internal/` folder with the new one.

Portable packages contain **only public example commands**, never personal notes, clipboard text, user-created command libraries, or private backups.

## Important notes

- Executables are **not code-signed**, so Windows SmartScreen or employer policies may restrict them; follow company device policy.
- Search and most utilities work offline. Network checks and IEEE-data downloads only require network access when explicitly invoked.
- The clipboard sensitive-text exclusion recognizes common credential patterns, but **cannot guarantee** that all secrets will be detected. Turn off capture or hide the Clipboard menu for sensitive work.
- Automated unit/GUI smoke tests and Windows packaged-EXE startup checks were run. Display scaling, native RTL editing, tray shortcuts and Windows menu interaction should still be verified on the user's device.
- **Smart Command Templates are not included** in this release; they will be developed separately after v1.29.
