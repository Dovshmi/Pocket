# PocketDesk

**A compact Windows system-tray toolbox for notes, shortcuts, network checks, and CLI commands.** Click its icon beside the clock to open a small popup instead of keeping another window on your desktop.

**Version 1.10** · Windows 10/11 · Python 3.10+ · Local-first · No account required

> **Public repository:** This source distribution includes a small synthetic CLI example library. The larger, workplace-derived command catalog from the private release is **not included**. The app supports that catalog locally when you supply it yourself.

![PocketDesk Command Helper with a taller results table](preview-commands-layout.png)

## Features

| Tab | Features |
| --- | --- |
| **Notes** | Multiple autosaved notes, a phone-number field per note, and one-click number copying. No caller-identification lookup. |
| **Shortcuts** | Launch websites, local files, or folders from the same popup. |
| **Ports** | Check individual or selected TCP ports for an IPv4/IPv6 target and export results to CSV. |
| **MAC** | Bulk MAC vendor lookup using public IEEE registries cached locally, with CSV import/export. |
| **Commands** | Machine-aware CLI references with searches across commands **and what they do**, temporary editing before copying, local custom commands, favorites, and recent copies. |

## Unified tall layout — new in v1.10

All five tabs now share the **850 px-tall** popup on a full-size display. This means more visible notes, shortcuts, port-check results, MAC results, and command entries. Switching tabs no longer changes the window size or shifts the popup on the desktop.

- The Commands tab keeps **Command on the left** and **Purpose / Description on the right** (right-aligned for Hebrew).
- The **Edit before copying** box is now **six lines high**, making it practical to adjust multi-line commands or command sequences before pressing **Copy edited**.
- On smaller screens, the popup automatically clamps to the available screen height; the command results list shrinks first, and the edit box can reduce to five lines so its buttons remain reachable.
- The selected command is **never executed**: only the contents of the editor are copied to your clipboard. Selecting a new command or pressing Reset discards your temporary changes.

![PocketDesk Commands tab with larger six-line edit box](preview-commands-layout.png)

## Command Helper — editing and saved commands

### 1. Modify a command before copying it

1. Open **COMMANDS** and pick a machine, or choose **All machines**.
2. Search by command text or description. Hebrew and English descriptions are supported.
3. Select a matching result to display its **editable command box**.
4. Replace placeholders such as `<INTERFACE>`, `<IP>`, or `<VLAN>` with actual values, or modify the CLI command however you need.
5. Click **Copy edited** (or press **Ctrl+Enter** when the editor is focused). The exact text in the editor is copied to your clipboard. **PocketDesk does not execute it.**
6. **Reset** restores the saved original command.

Edits to the copy box are **temporary**. They do **not** change the imported reference or save automatically; choosing a different result resets the editor. This makes it safe to reuse a known command template repeatedly.

### 2. Add commands to a machine

1. Select the machine from the dropdown (for example **Cisco** or **Fortigate**) and click **+ New**.
2. Supply a **purpose/description**, **category**, and **command** (multiple lines are supported).
3. Click **Save command**. The command appears in the selected machine's search results immediately and is saved to your PC.
4. To create a new machine category, choose **All machines**, click **+ New**, then type a new machine name in the Machine field.
5. To change your own saved command permanently, select it and click **Edit saved**. To remove it, use **Delete** (with confirmation).

Add commands with the **+ New** button in the Commands tab.

**Searchability:** Custom commands use the same filters as the original catalog. They are searchable by their command text, purpose/description, machine, and category; they also support **★ Saved** and **Recent**. Editing a custom command retains its identity and favorite status.

**Original commands stay read-only.** The starter command pack from the private workbook is not overwritten. Temporary edits don't affect it; creating or editing a personal command is a deliberate separate action.

### 3. Useful keyboard controls

- `Ctrl+F` — focus the command search field while on the Commands tab
- `Ctrl+Enter` — copy the current edited command when editing
- `Ctrl+A` — select all text in the command editor
- `Ctrl+S` — save application data immediately
- `Esc` — hide the popup, or close the New/Edit command dialog

## Installation

1. Clone the repository with `git clone https://github.com/Dovshmi/Pocket.git` (or download and extract its source ZIP).
2. Install [Python 3.10+ for Windows](https://www.python.org/downloads/windows/) (the normal Windows installer includes Tkinter).
3. Run **`run.bat`**.
4. Click the PocketDesk icon in the notification area next to the clock. If you don't see it, open the `^` hidden-icons menu.

To build a standalone **PocketDesk.exe**, double-click **`build-exe.bat`** on Windows. The executable appears in `dist\PocketDesk.exe`. The public build bundles sample commands. If you placed a private `commands/commands.json` file in your local checkout, the build script uses it instead; **do not publicly distribute the resulting EXE without reviewing that data**.

The app uses the Python standard library at runtime. PyInstaller is used only to build the EXE.

## Data, privacy, and upgrades

PocketDesk saves your data under **`%APPDATA%\PocketDesk\`**:

| File | Contents |
| --- | --- |
| `data.json` | Notes, optional phone numbers, shortcuts, port preferences, **personal custom commands**, favorites, and command-history preferences |
| `vendors.json` | IEEE vendor-prefix cache for MAC lookups, if downloaded |

Existing data from previous releases, including v1.6 and v1.7, is loaded with backward-compatible defaults. The v1.10 updater does not remove saved notes or shortcuts.

The public repository includes `commands/example_commands.json`, a **small generic offline example library**. The private release contains a separate `commands/commands.json` file derived from a workplace workbook (573 curated entries, 30 equipment categories). That file is **not committed to GitHub**. The original workbook is not distributed. Both read-only libraries work with the same editor and search features. See [`commands/README.md`](commands/README.md).

**Important:** The workbook originally contained workplace credentials and operational information. Although the private command pack was filtered and many identifiers generalized, it has **not been certified free of confidential operational data**. Keep the private ZIP and any EXE built with that pack private; `.gitignore` excludes `commands/commands.json`. **Do not publish this command pack to GitHub.** The custom commands in `data.json` are stored in plain text locally; don't put passwords, tokens, or private keys in them or in CLI clipboard drafts.

PocketDesk does not upload your commands, search history, notes, or custom entries. It makes network requests only when you start a TCP port check or an IEEE vendor-database update. A copied command can be read by other software accessing the system clipboard.

## Testing

From the project folder on Windows:

```powershell
py -3 -m unittest discover -v
```

Graphical checks (optional, require Tkinter and Pillow) include `smoke_commands.py`, `smoke_custom_commands.py`, `smoke_command_layout.py`, `smoke_unified_layout.py`, and `smoke_ui.py`. The new layout smoke test checks the reversed columns, Hebrew alignment, larger six-line editor, and consistent window height across all five tabs using synthetic test data. The command tools have been tested on a Linux graphical virtual display, including editing a command before copying, saving/reloading custom commands, editing favorites, and deleting custom entries. **Native Windows system-tray behavior and the Windows EXE remain to be tested on Windows itself.**

## Project layout

```text
PocketDesk/
├── app.pyw                # System-tray dashboard and five tabs
├── command_helper.py      # Command filtering, validation, custom-command handling
├── commands/
│   ├── example_commands.json # Public, generic example references
│   ├── commands.json      # Optional PRIVATE catalog; ignored by Git
│   └── README.md
├── network_tools.py       # TCP port check and MAC vendor logic
├── shortcut_utils.py      # Local and web shortcut handling
├── assets/                 # Tray icon
├── run.bat                 # Launch on Windows with Python
├── build-exe.bat           # Build a standalone Windows EXE
├── requirements-build.txt # PyInstaller
├── test_*.py               # Automated tests
├── smoke_*.py              # Optional GUI checks
└── .gitignore              # Protect private/data files and build output
```

## Troubleshooting

**I can't see my new command.** Choose the correct machine, change the view to **All**, set the category to **All categories**, and clear the search.

**The popup looks too tall on my screen.** PocketDesk clamps all five tabs to the usable display height. On the Commands tab, the results table can be scrolled and yields space to the editor on smaller screens.

**The editor changed, but my stored command did not.** Edits in the copy box are intentionally temporary. For your own custom commands, use **Edit saved** to make a permanent change.

**My commands disappear after restarting.** Check whether `%APPDATA%\PocketDesk\data.json` can be written by your Windows account. Personal commands are stored there, not next to the EXE.

**The Commands tab has no built-in commands.** Verify that `commands/example_commands.json` is present alongside `app.pyw` when running from source. Optionally, place your private `commands/commands.json` locally to load it instead. The build script bundles the selected library in the EXE.

**No icon in the tray?** Check the hidden `^` tray icons and whether `run.bat` is running. Launch `py -3 app.pyw --preview` for a regular window when troubleshooting.

## License

Code usage follows the license in the GitHub repository. The **private command pack is not offered for redistribution** under that license; review it separately and obtain authorization before sharing it.
