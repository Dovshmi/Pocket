<div align="center">

# Pocket

**Your everyday tools, one shortcut away.**

A compact Windows tray utility for quick notes, saved shortcuts, network diagnostics, CLI references, and subnet planning.

**Windows 10 / 11** · **Python 3.10+** · **v1.25** · **Local-first** · **GPL-3.0**

[Features](#features) · [App gallery](#app-gallery) · [Installation](#getting-started) · [Build an EXE](#building-a-windows-executable) · [Changelog](#version-history)

</div>

<p align="center">
  <a href="preview-window-position.png"><img src="preview-window-position.png" width="420" alt="Pocket desktop tray utility showing its Notes view"></a>
</p>

> [!NOTE]
> **Development status:** Pocket is actively developed. This repository includes source code rather than a prebuilt Windows release. The existing gallery images are real screenshots from previous development builds; current screenshots are being prepared separately.


## What is Pocket?

Pocket is designed for tasks that are too small to justify opening another full-size app: jotting down a phone number, launching a frequently used folder, checking a TCP port, identifying a MAC vendor, finding a CLI command or calculating a subnet.

It stays out of the way until you need it, and stores your personal notes and preferences **on your own computer**.

## App gallery

Seven tools plus Settings, presented in a small movable window. All images below are **real application captures**, although some show earlier builds of the interface.

<table>
  <tr>
    <td align="center" width="33%"><a href="preview-notes-pinned-v117.png"><img src="preview-notes-pinned-v117.png" width="220" alt="Pocket Notes screen"></a><br><strong>Notes</strong><br><sub>Autosave, pin and organize</sub></td>
    <td align="center" width="33%"><a href="preview-shortcuts-fixed.png"><img src="preview-shortcuts-fixed.png" width="220" alt="Pocket Shortcuts screen"></a><br><strong>Shortcuts</strong><br><sub>Sites, files and folders</sub></td>
    <td align="center" width="33%"><a href="preview-ports.png"><img src="preview-ports.png" width="220" alt="Pocket TCP port checker"></a><br><strong>TCP Ports</strong><br><sub>Fast connectivity checks</sub></td>
  </tr>
  <tr>
    <td align="center"><a href="preview-mac.png"><img src="preview-mac.png" width="220" alt="Pocket MAC vendor lookup"></a><br><strong>MAC Lookup</strong><br><sub>IEEE OUI identification</sub></td>
    <td align="center"><a href="preview-commands-layout.png"><img src="preview-commands-layout.png" width="220" alt="Pocket CLI command helper"></a><br><strong>Commands</strong><br><sub>Search, edit and copy</sub></td>
    <td align="center"><a href="preview-subnet-v117.png"><img src="preview-subnet-v117.png" width="220" alt="Pocket subnet calculator"></a><br><strong>Subnet Calculator</strong><br><sub>CIDR and network splits</sub></td>
  </tr>
</table>

Additional detail captures: [Notes actions](preview-note-context-menu.png) · [Shortcut drag-and-drop](preview-shortcuts-drop.png) · [Command editor](preview-commands-edit.png) · [Saved window position](preview-window-position.png).

## Features

### Seven tools in one window

| Tool | Capabilities |
|:---|:---|
| **Notes** | Autosaved notes with titles, phone-number fields and creation dates. Full-width editor; pin, duplicate and delete notes; text-editing context menu; insert date/time; export the current note to Notepad. Select an IP to send it to Ports, or CLI text to search in Commands. |
| **Shortcuts** | Save and open websites, local files and folders. Add shortcuts manually or by dragging items from your browser/File Explorer into a review form. The **compact live search** filters saved shortcuts by name, destination and type. |
| **TCP Ports** | Test one TCP port, predefined ports, or a custom list/range against an IPv4 or IPv6 address. See **OPEN**, **CLOSED**, **TIMEOUT** and **ERROR** results, with copy/export options. |
| **MAC Lookup** | Look up hardware vendors using IEEE OUI prefix assignments. Supports multiple MAC addresses, downloading/importing registry data, offline lookup after caching, and CSV export. |
| **Commands** | Search a network CLI library by device, category, syntax or purpose (including Hebrew). Edit before copying; favorite, add, edit and delete saved entries. Uses one writable `commands.json` with manual backup and restore. **Commands are never executed.** |
| **Subnet Calculator** | IPv4 CIDR/netmask calculations: network and broadcast, wildcard mask, first/last usable address, usable/total address counts, and subdivision into smaller networks. Includes `/31` and `/32` handling. |
| **Clipboard** | Menu-visibility-controlled session-only clipboard history for text, with search, pin, copy-back, clear and delete. No captured content is saved to disk. |

### Personalize the workspace

**Settings (⚙)** controls which tool tabs are visible. Adding **Clipboard** starts monitoring copied text while Pocket runs; hiding it stops monitoring. There is no separate clipboard switch. Hidden tabs keep their saved data; extra tools appear under **MORE**. Copied text is only stored in memory.

| Feature | How it works |
|:---|:---|
| **Six color themes** | Click the **pocket logo** to choose Blue, Dark Blue, Black, Red, Green or Purple. Pocket updates the window colors, in-app logo and tray icon, then remembers your choice. |
| **Your own popup shortcut** | Click the shortcut label directly beneath **Pocket** to select Ctrl/Alt/Shift/Win modifiers and a key. Default: **Ctrl + Shift + \***. If Windows cannot register a new combination, the previous working shortcut is retained. |
| **Move and remember** | Drag the header to move the popup. The position is saved and restored. Right-click the header → **Reset window position**. |
| **PIN mode** | Keep Pocket visible when you switch to another app — useful for copying information and dragging shortcuts. |
| **System tray** | Click the tray icon to show/hide Pocket. The close button hides the popup; it doesn't erase your notes. |
| **Note reminders** | In Notes, check **Notify me…** for an individual note, choose the local date and time, and receive a Windows tray notification when due. Clicking it opens the note. Pocket must be running; overdue reminders fire after restart. |
| **Menu visibility** | Show/hide individual tool tabs under Settings, without removing any saved data. |

**Note on icons:** The live window and system-tray icons change with your selected theme. The compiled EXE retains its **blue embedded icon**, and Windows can cache desktop/taskbar shortcut artwork.

## Getting started

### Requirements

- **Windows 10 or 11** (tray integration and global popup shortcuts use native Windows APIs).
- **Python 3.10 or newer**, installed with Tkinter and the Windows Python launcher (`py`).
- Internet access for first-time dependency installation and optional IEEE vendor-database updates.

### Run from source

**Option A — download a ZIP:** [Download the latest source](https://github.com/Dovshmi/Pocket/archive/refs/heads/main.zip), extract it, and open the extracted folder.

**Option B — clone the repository:**

```powershell
git clone https://github.com/Dovshmi/Pocket.git
cd Pocket
```

Then:

1. Double-click **`install.bat`** to install the Python dependencies (including Pillow for the themed icons).
2. Double-click **`run.bat`** to launch Pocket.
3. Find the Pocket icon in the notification area, near the Windows clock. If hidden, click the **^** overflow arrow.
4. Click the tray icon or use **Ctrl + Shift + \*** to toggle the popup.

You can also install and launch manually:

```powershell
py -3 -m pip install -r requirements.txt
py -3 app.pyw
```

> **Why run `install.bat` first?** `run.bat` contains a first-run check for drag-and-drop support, but that check alone may not install the newer **Pillow** dependency on an existing setup. Running `install.bat` installs all declared dependencies.

### First things to try

1. Open **Notes** and create a note. It will autosave to your local data file.
2. Open **Shortcuts**, add a website or folder, and try the compact search field.
3. Click the **pocket logo** to change themes.
4. Click the **shortcut text under Pocket** to configure your own show/hide keys.
5. Open **Subnet** and try `192.168.1.10/24` or a `/26` subdivision.

## Building a Windows executable

To build a standalone executable on **Windows**, run:

```bat
build-exe.bat
```

The script installs build requirements, generates the blue embedded icon, and uses PyInstaller to produce:

```text
dist\PocketDesk.exe
```

The generated executable name remains **PocketDesk.exe**, while the window header says **Pocket**.

> [!WARNING]
> **Do not publish an EXE built with a private command library.** The build script uses `commands/commands.json` if it exists locally, which can bundle that file inside the executable. Build public artifacts without a private `commands/commands.json`. No prebuilt EXE is included in this repository.

**Packaging caveat:** Native Windows tray interaction, hotkey registration, icon refresh and multi-monitor behavior should be tested on a Windows machine before distributing a build. Passing headless tests alone does not validate those integrations.

## Files, settings and privacy

Pocket saves user data under:

```text
%APPDATA%\PocketDesk\
├── data.json            # Notes, shortcuts, theme, hotkey, window position, preferences
├── vendors.json         # Cached or imported IEEE vendor data
├── icons\               # Locally generated color icon variants (PNG / ICO)
└── notepad_exports\     # Exported .txt snapshots of notes
```

- **Local-first:** no account, hosted database or synchronization service is required.
- **Not encrypted:** notes, phone numbers and custom commands are saved in **plain-text JSON**. Avoid keeping credentials or secrets there.
- **Notepad is an export:** opening a note in Windows Notepad creates a snapshot; later Notepad edits **do not sync back** to Pocket.
- **Network activity:** TCP checks contact only the specified target. Registry downloads retrieve IEEE vendor data when requested. Pocket doesn't send notes to a lookup service.
- **Authorization:** only scan systems you own or are authorized to test. A port timeout does not prove a port is closed.
- **MAC limitations:** an OUI indicates a registered vendor prefix, not proof of the exact device manufacturer or owner.

### CLI command library

The Commands tab uses **one writable JSON library**: `commands/commands.json`. Commands may be searched by machine and category, edited in-place, copied, favorited, or deleted. Atomic saves protect changes. **Backups are manual only**: choose **Backup ▾ → Create new backup** or **Use existing backup** to restore a previously saved JSON file. Adding, editing, and deleting commands never creates a backup automatically. See [the example format](commands/example_commands.json).

> [!WARNING]
> **Public-repository review needed:** A command library is currently checked into this public repository, including a second copy at `Pocket_Commands_One_Library/commands/commands.json`. Review both copies for internal device names, infrastructure details, or other sensitive material before sharing. The `.gitignore` rule does **not** retroactively remove committed files. Do not commit secrets or workplace-only command collections.

The local application does not upload command edits automatically; GitHub publishing is a separate action.

> **Packaging caution:** Review the source library before building an EXE: a local `commands/commands.json` may be bundled inside it. Do not distribute a build containing private commands.

## Project structure

```text
Pocket/
├── app.pyw                 # Desktop UI, notes, tabs and tray
├── icon_themes.py          # Theme palettes and generated icons
├── hotkey_settings.py      # Configurable popup shortcut
├── command_helper.py       # Command search and editing
├── command_store.py        # Atomic command saves and manual backup/restore
├── machine_catalog.py      # Machine category support
├── network_tools.py        # Port tests and MAC lookup
├── subnet_calculator.py    # IPv4 calculations
├── shortcut_utils.py       # Shortcut handling
├── shortcut_drop.py        # Drag-and-drop support
├── commands/
│   ├── commands.json           # Currently tracked command data; review before sharing
│   ├── example_commands.json   # Example format
│   └── README.md
├── install.bat / run.bat   # Set up and launch
├── build-exe.bat           # Package a Windows executable
├── test_*.py               # Unit tests
└── smoke_*.py              # Optional GUI smoke checks
```

**Stack:** Python, Tkinter/ttk, Win32 APIs via `ctypes`, Pillow, `tkinterdnd2` and PyInstaller.

## Version history

Development milestones shown below are drawn from repository commits and feature implementations; they are **not** a claim that each intermediate version has a separate downloadable GitHub Release.

| Version | Date | Highlights |
|:---|:---|:---|
| **v1.25** | 2026-10-28 | Restored one local commands.json library; removed public-command loading, with machine names optionally included in that JSON. |
| **v1.22** | 2026-10-28 | Full machine catalogue (32 named categories), 32 additional read-only CLI examples, and merged public/private/custom references. |
| **v1.21** | 2026-10-28 | Expanded public network CLI catalogue to 118 entries; fixed dependency detection, empty TCP scan and private command-file fallback. |
| **v1.20** | 2026-10-28 | App header renamed to **Pocket**, clickable configurable global hotkey, compact live Shortcuts search. |
| **v1.19** | 2026-10-28 | Six saved themes and matching live app/tray icons. |
| **v1.18** | 2026-10-27 | Movable popup with persistent positioning and reset action. |
| **v1.17** | 2026-10-27 | Subnet calculator and note pin/duplicate/delete actions; integrated into the v1.18 commit. |
| **v1.16** | 2026-10-27 | Full-width note editor, expanded context actions, shortcut-layout fixes. |
| **v1.10** | 2026-10-27 | Unified tall layout and multiline command editing. |
| **v1.6** | 2026-10-26 | Initial functional tray toolbox with notes, shortcuts and network tools. |

View the complete [commit history](https://github.com/Dovshmi/Pocket/commits/main).

## Testing and development

After installing dependencies, run all discoverable unit tests:

```powershell
py -3 -m unittest discover -v
```

The project includes tests for data storage/migration, theme settings, generated icons, configurable hotkeys, shortcut filtering, subnet calculations, command management, note actions and network utilities.

GUI smoke scripts are provided separately (see `smoke_*.py`) and need a functioning display. **The repository does not currently claim a verified Windows CI release pipeline.** The new command coverage tests are source-level checks, not proof that every command works on every vendor model and firmware.

## Contributing and feedback

Bug reports, ideas and pull requests are welcome.

- [Open an issue](https://github.com/Dovshmi/Pocket/issues) with reproduction steps, Windows/Python versions, and relevant error details (remove private information from screenshots/logs).
- For code changes, keep features focused and add or update tests when applicable.
- Run `py -3 -m unittest discover -v` before proposing a pull request.
- Never upload local `data.json`, passwords, or private command packs. Review the command data already tracked in the repository.

## License

Licensed under the [GNU General Public License v3.0](LICENSE).

---

<div align="center">

**Pocket** — a small toolbox for the things you do all day.

[Back to top](#pocket)

</div>
