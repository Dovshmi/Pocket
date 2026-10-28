<div align="center">

# Pocket

### Your notes, shortcuts and network tools — one click away.

A compact, customizable Windows desktop toolbox that lives in your system tray. Open it when you need it, keep your tools close, and get back to work.

**Windows 10 / 11** · **Python 3.10+** · **Current version: v1.23** · **GPL-3.0** · **Local-first**

[Explore the app](#screenshots) · [Features](#features) · [Get started](#getting-started) · [Build an EXE](#building-a-windows-executable) · [Version history](#version-history)

</div>

<p align="center">
  <a href="preview-window-position.png">
    <img src="preview-window-position.png" alt="Pocket desktop app showing the Notes interface, with the draggable window positioned on screen" width="440">
  </a>
</p>

> [!NOTE]
> **Project status:** Pocket is under active development. The repository contains the application **source code**, not a downloadable prebuilt Windows release. Screenshots below are genuine captures from earlier development versions; some header and toolbar details have changed in v1.19–v1.20.

## Why Pocket?

Pocket is designed for tasks that are too small to justify opening another full-size app: jotting down a phone number, launching a frequently used folder, checking a TCP port, identifying a MAC vendor, finding a CLI command or calculating a subnet.

It stays out of the way until you need it, and stores your personal notes and preferences **on your own computer**.

## Screenshots

These are screenshots of the **actual Pocket application**, not UI mockups. Select a screenshot for a closer look.

<table>
<tr>
<td align="center" width="33%">
  <a href="preview-notes-pinned-v117.png"><img src="preview-notes-pinned-v117.png" width="220" alt="Notes with pinned notes and full-width text editor"></a><br>
  <b>Notes</b><br><sub>Capture from v1.17</sub>
</td>
<td align="center" width="33%">
  <a href="preview-shortcuts-fixed.png"><img src="preview-shortcuts-fixed.png" width="220" alt="Quick-launch website, file and folder shortcuts"></a><br>
  <b>Shortcuts</b><br><sub>Earlier development capture</sub>
</td>
<td align="center" width="33%">
  <a href="preview-ports.png"><img src="preview-ports.png" width="220" alt="TCP port checker and scan results"></a><br>
  <b>TCP Ports</b><br><sub>Earlier development capture</sub>
</td>
</tr>
<tr>
<td align="center">
  <a href="preview-mac.png"><img src="preview-mac.png" width="220" alt="MAC vendor lookup results"></a><br>
  <b>MAC Lookup</b><br><sub>Earlier development capture</sub>
</td>
<td align="center">
  <a href="preview-commands-layout.png"><img src="preview-commands-layout.png" width="220" alt="Network CLI command search and editing panel"></a><br>
  <b>Commands</b><br><sub>Earlier development capture</sub>
</td>
<td align="center">
  <a href="preview-subnet-v117.png"><img src="preview-subnet-v117.png" width="220" alt="IPv4 subnet calculation and subdivision"></a><br>
  <b>Subnet Calculator</b><br><sub>Capture from v1.17</sub>
</td>
</tr>
</table>

More interface views: [note right-click menu](preview-note-context-menu.png) · [shortcut drag-and-drop](preview-shortcuts-drop.png) · [editable CLI command](preview-commands-edit.png) · [saved window position](preview-window-position.png).

## Features

### Six tools in one popup

| Tool | Capabilities |
|:---|:---|
| **Notes** | Autosaved notes with titles, phone-number fields and creation dates. Full-width editor; pin, duplicate and delete notes; text-editing context menu; insert date/time; export the current note to Notepad. Select an IP to send it to Ports, or CLI text to search in Commands. |
| **Shortcuts** | Save and open websites, local files and folders. Add shortcuts manually or by dragging items from your browser/File Explorer into a review form. The **compact live search** filters saved shortcuts by name, destination and type. |
| **TCP Ports** | Test one TCP port, predefined ports, or a custom list/range against an IPv4 or IPv6 address. See **OPEN**, **CLOSED**, **TIMEOUT** and **ERROR** results, with copy/export options. |
| **MAC Lookup** | Look up hardware vendors using IEEE OUI prefix assignments. Supports multiple MAC addresses, downloading/importing registry data, offline lookup after caching, and CSV export. |
| **Commands** | Search a network CLI reference library by device, category, command syntax or description (including Hebrew text). Edit a command before copying, save favorites, and create your own machine/category/command entries. **Never executes commands.** |
| **Subnet Calculator** | IPv4 CIDR/netmask calculations: network and broadcast, wildcard mask, first/last usable address, usable/total address counts, and subdivision into smaller networks. Includes `/31` and `/32` handling. |

### Personalize the workspace

| Feature | How it works |
|:---|:---|
| **Six color themes** | Click the **pocket logo** to choose Blue, Dark Blue, Black, Red, Green or Purple. Pocket updates the window colors, in-app logo and tray icon, then remembers your choice. |
| **Your own popup shortcut** | Click the shortcut label directly beneath **Pocket** to select Ctrl/Alt/Shift/Win modifiers and a key. Default: **Ctrl + Shift + \***. If Windows cannot register a new combination, the previous working shortcut is retained. |
| **Move and remember** | Drag the header to move the popup. The position is saved and restored. Right-click the header → **Reset window position**. |
| **PIN mode** | Keep Pocket visible when you switch to another app — useful for copying information and dragging shortcuts. |
| **System tray** | Click the tray icon to show/hide Pocket. The close button hides the popup; it doesn't erase your notes. |

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
> **Do not publish an EXE built with a private command library.** The build script uses `commands/commands.json` if it exists locally, which can bundle that file inside the executable. Build public artifacts from a clean checkout containing only `commands/sample_commands.json`. No prebuilt EXE is included in this repository.

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

### Private CLI commands

The public repository ships with a **150-entry public command library** for Cisco, FortiGate, Juniper and Nokia SR OS. To maintain your own reference collection, create:

```text
commands/commands.json
```

Pocket now combines that local file with the built-in `commands/sample_commands.json` and `commands/public_additions.json` libraries. Machine categories are populated from `commands/machine_catalog.json` even when no verified command exists for a category. The private path is ignored by Git. **Do not commit workplace commands, passwords, IP inventories or sensitive operational data.**

See [commands/README.md](commands/README.md) for the command-library convention.


### Your command library (single-file mode)

Pocket uses **only one command reference file**: `commands/commands.json` in your Pocket folder. It does not install or load any public command library. For a packaged EXE, place the same file next to the EXE under `commands/commands.json`; the app also supports a separately supplied local file in your AppData folder. The optional `machines` array in this JSON makes equipment categories visible even when they have no CLI entries. Commands added inside the app are stored locally in `data.json` as before.

**Never publish this file** if it includes workplace-specific operational data. The public GitHub source does not include your workbook or uploaded private command reference. To build an EXE, copy your private `commands.json` into the `commands` folder first; the EXE build will bundle it, so do not distribute that EXE publicly without reviewing its content.

## Project structure

```text
Pocket/
├── app.pyw                 # Tkinter interface, notes, tabs, Windows tray
├── icon_themes.py          # Six color palettes and icon generation
├── hotkey_settings.py      # Custom hotkey mapping and shortcut filtering
├── command_helper.py       # CLI reference search and user commands\n├── machine_catalog.py      # Full machine selector and library merging
├── network_tools.py        # TCP checks and MAC vendor lookup
├── subnet_calculator.py    # IPv4 network calculations
├── shortcut_utils.py       # Shortcut handling
├── shortcut_drop.py        # Drag-and-drop parsing
├── commands/
│   ├── sample_commands.json\n│   ├── public_additions.json\n│   └── machine_catalog.json
├── assets/                 # App assets and default icon
├── install.bat             # Dependency installation
├── run.bat                 # Start the application
├── build-exe.bat           # Build a Windows EXE
├── test_*.py               # Unit tests
└── smoke_*.py              # Optional GUI smoke tests
```

**Stack:** Python, Tkinter/ttk, native Win32 APIs via `ctypes`, Pillow, `tkinterdnd2`, PyInstaller for packaging. Pocket does not require a separate backend.

## Version history

Development milestones shown below are drawn from repository commits and feature implementations; they are **not** a claim that each intermediate version has a separate downloadable GitHub Release.

| Version | Date | Highlights |
|:---|:---|:---|
| **v1.23** | 2026-10-28 | Restored one local commands.json library; removed public-command loading, with machine names optionally included in that JSON. |\n| **v1.22** | 2026-10-28 | Full machine catalogue (32 named categories), 32 additional read-only CLI examples, and merged public/private/custom references. |\n| **v1.21** | 2026-10-28 | Expanded public network CLI catalogue to 118 entries; fixed dependency detection, empty TCP scan and private command-file fallback. |\n| **v1.20** | 2026-10-28 | App header renamed to **Pocket**, clickable configurable global hotkey, compact live Shortcuts search. |
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
- Never upload local `data.json`, `commands/commands.json`, passwords or private command packs.

## License

Licensed under the [GNU General Public License v3.0](LICENSE).

---

<div align="center">

**Pocket** — a small toolbox for the things you do all day.

[Back to top](#pocket)

</div>
