<div align="center">

<img src="assets/app.png" width="82" alt="Pocket app icon" />

# Pocket

**Your everyday tools, one shortcut away.**

A compact, local-first Windows tray toolbox for notes, network diagnostics, shortcuts and CLI references.

<p>
  <img src="https://img.shields.io/badge/Release-v1.28-8B80F9?style=for-the-badge" alt="Pocket v1.28" />
  <img src="https://img.shields.io/badge/Windows-10_%2F_11-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10 and 11" />
  <img src="https://img.shields.io/badge/Python-Tkinter-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python and Tkinter" />
  <img src="https://img.shields.io/badge/Portable-ZIP-0F766E?style=for-the-badge" alt="Portable ZIP" />
  <img src="https://img.shields.io/badge/Local--first-No_Account-334155?style=for-the-badge" alt="Local-first" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-64748B?style=for-the-badge" alt="GPL-3.0" />
</p>

**[Download Pocket v1.28](https://github.com/Dovshmi/Pocket/releases/tag/v1.28)** · **[Portable ZIP](https://github.com/Dovshmi/Pocket/releases/download/v1.28/Pocket-Portable-v1.28.zip)** · **[Source](https://github.com/Dovshmi/Pocket)**

</div>

---

## Overview

**Pocket** is a lightweight utility that stays in your Windows system tray until you need it. Save a note or phone number, open a shortcut, check a TCP port, identify a MAC vendor, search a CLI reference or calculate an IPv4 subnet—all from one small window.

Pocket offers **Normal** and **Mini** layouts, six saved visual themes, local data storage and optional one-shot note reminders. The portable release runs without installing Python on the destination PC.

## Experimental Dashboard and Compact layouts (development branch)

> **In development:** This layout is available on the `feature/dashboard-ui-refresh` branch, not in the published v1.28 download or on `main`. It adapts the earlier promotional concept art to the existing **Tkinter Windows app**; the concept images are not screenshots and some illustrated capabilities are not Pocket features.

Pocket now has four layouts:

| Layout | Size | Purpose |
|:---|:---|:---|
| **Normal** | 480 × 850 | Original tray-first popup; remains the default. |
| **Mini** | 346 × 530 | Compact icon navigation and quick access. |
| **Dashboard** | 1160 × 800 | Wide desktop workspace with a permanent left sidebar, dashboard home, and the original functional tools. |
| **Compact** | 820 × 680 | Smaller dashboard with a slim left menu and compact overview; all real tools accessible. |

**What Compact includes:** a 144 px sidebar with a button for each enabled tool, always-accessible Settings, a compact header with PIN, hide, theme, hotkey and CLI-search actions, an overview showing real counts and links to every enabled menu, and separately saved position. The tool pages reuse Pocket's actual Notes, Shortcuts, TCP Ports, MAC Lookup, Commands, Subnet, Clipboard and Settings implementations. Lengthy Home, Settings and networking tool pages scroll instead of truncating controls. Clipboard remains in-memory only; commands do not execute.

**What Dashboard includes:** a themed left navigation rail (respecting visible menus), a home page with real counts of saved notes, shortcuts, CLI references and session clipboard items, quick links into existing tools, a top command-search action, native window dragging, theme selection, PIN and saved dashboard-specific position. Notes and CLI views take advantage of the extra horizontal space. All controls route to existing Pocket tools; no demonstration or placeholder network actions are introduced.

**Try it from source (Windows):**

```powershell
git clone --branch feature/dashboard-ui-refresh https://github.com/Dovshmi/Pocket.git
cd Pocket
install.bat
run.bat
```

In Pocket choose **Settings → Compact** for the smaller new dashboard or **Settings → Dashboard** for the larger version. Switch back with **Settings → Normal** or **Settings → Mini**. The existing `data.json` and `commands.json` formats and command backup behavior remain intact. Each layout remembers its own position. **Normal remains the default for new installations.**

**Important differences from concept art:** no artificial favorites panels, editable rich-text toolbar, binary subnet visualization, or universal home search are added merely because they appear in generated images. Only real application functionality is presented. Commands are still copied, never executed. Clipboard data remains session-only; note reminders still require Pocket to run in the tray. Do not use concept images as evidence of implemented functionality.

### Development and testing

Dashboard and Compact are optional UI layers (`dashboard_ui.py` and `compact_dashboard.py`) that reuses the existing `PocketDesk` tool builders. The branch includes display-mode storage tests and a Windows/Linux unit-test workflow. **Visual behavior, window scaling and native editor placement still need hands-on testing on Windows before release.**

---

## Interface preview

> **Illustrated UI previews (v1.28):** These SVGs depict the current Normal/Mini layouts and key controls. They are **not actual Windows screenshots**, and the sample notes/commands shown are illustrative. See the [legacy screenshot archive](#legacy-screenshot-archive) for real captures of earlier builds.

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="docs/images/pocket-v128-normal-notes.svg" width="340" alt="Illustrated Pocket Normal Notes view with note list, title, phone, reminder and full-width editor" /><br/><strong>Normal · Notes</strong></td>
      <td align="center"><img src="docs/images/pocket-v128-mini-notes.svg" width="243" alt="Illustrated Pocket Mini Notes view with icon navigation and compact note editor" /><br/><strong>Mini · Notes</strong></td>
    </tr>
    <tr>
      <td align="center"><img src="docs/images/pocket-v128-normal-commands.svg" width="340" alt="Illustrated Normal Commands view with four result rows and editing pane" /><br/><strong>Normal · Commands</strong></td>
      <td align="center"><img src="docs/images/pocket-v128-mini-mac.svg" width="243" alt="Illustrated Mini MAC vendor lookup form" /><br/><strong>Mini · MAC lookup</strong></td>
    </tr>
  </table>
</div>

### Legacy screenshot archive

The images below are **real screenshots from earlier Pocket versions**, preserved for reference; some controls, spacing and menus have since changed.

| Notes | Shortcuts | Network tools |
|:---:|:---:|:---:|
| <img src="preview-notes-pinned-v117.png" width="195" alt="Legacy v1.17 Notes screenshot" /> | <img src="preview-shortcuts-fixed.png" width="195" alt="Legacy Shortcuts screenshot" /> | <img src="preview-ports.png" width="195" alt="Legacy TCP Ports screenshot" /> |

## Features

### Seven tools in one window

| Tool | Capabilities |
|:---|:---|
| **Notes & reminders** | Autosaved notes with titles, phone fields and creation dates. Pin, duplicate, delete, use right-click text actions, select per-note RTL/LTR direction (a single native Windows Unicode editor for both modes), insert timestamps, or edit in Notepad with saved changes imported into Pocket. Enable **Notify me…** on an individual note to schedule a one-time Windows notification. Selected IPs and CLI text can be sent to their respective tools. |
| **Shortcuts** | Save and open websites, local files and folders. Add shortcuts manually or by dragging items from your browser/File Explorer into a review form. The **compact live search** filters saved shortcuts by name, destination and type. Each shortcut card has direct **Open**, **Copy**, and overflow-menu actions. |
| **TCP Ports** | Test one TCP port, predefined ports, or a custom list/range against an IPv4 or IPv6 address. See **OPEN**, **CLOSED**, **TIMEOUT** and **ERROR** results, with copy/export options. |
| **MAC Lookup** | Look up hardware vendors using IEEE OUI prefix assignments. Supports multiple MAC addresses, downloading/importing registry data, offline lookup after caching, and CSV export. |
| **Commands** | Search a network CLI library by device, category, syntax or purpose (including Hebrew). Edit before copying; favorite, add, edit and delete saved entries. Uses one writable `commands.json` with manual backup and restore. **Commands are never executed.** |
| **Subnet Calculator** | IPv4 CIDR/netmask calculations: network and broadcast, wildcard mask, first/last usable address, usable/total address counts, and subdivision into smaller networks. Includes `/31` and `/32` handling. |
| **Clipboard** | Searchable, session-only history of copied **text**. Pin entries, copy an item back to Windows, or delete/clear history. Monitoring automatically runs while Clipboard is visible in Settings; captured text is **not persisted**. |

### Mini Mode

Open **Settings → Switch to Mini mode** to change Pocket to a compact **346 × 530 px** view. Return with **Settings → Return to Normal size**. The display mode is saved across restarts. There is **no title-bar mode toggle**.

- A compact header uses an always-visible **icon tab for every enabled tool**, with a short caption and active highlighting — no dropdown. Settings, PIN, close and themes remain accessible.
- **Normal Commands** shows **four full result rows** above the editor, with a resizable divider. **+ New** and **Backup ▾** sit beside a fixed heading above the scrollable content, freeing a separate toolbar row; only Mini retains the original card layout.
- **Normal-mode scrolling:** Ports, MAC Lookup, Commands and Subnet scroll vertically with the mouse wheel or touchpad **without a visible outer scrollbar**, including on short monitors and high-DPI Windows scaling. Tables retain their own scrollbars; editable text fields continue to scroll when their content overflows. **Mini's outer scrollbar is hidden too**, while its mouse-wheel scrolling remains available. The Commands machine and category dropdowns no longer change selection when the wheel is used over them in either Normal or Mini; in Normal, the wheel scrolls the page instead.
- **Mini Commands** presents the most relevant CLI match first in one editable card. Use ◀ / ▶ to browse results, or the keyboard arrow keys **when focus is outside the command editor, search box and other input controls**. Favorites, Recents, device/category search, Copy, Edit, Delete, Reset and manual backup remain available; nothing executes commands.
- **Notes** combines the note picker, compact page counter and ◀ / ▶ arrows in **one row** above the metadata, freeing vertical space for typing. Pinned notes remain first; keyboard paging works outside input fields. The Windows RTL/LTR editor, reminders and Notepad synchronization are unchanged.
- **Shortcuts** uses denser rows with direct Open, Copy and overflow actions.
- **Ports, MAC Lookup and Subnet** use scrollable views with compact result tables. Entering Mini Mode never initiates a network connection. For IEEE MAC registries, **Update IEEE DB** tries the official CSV downloads; **Get CSV ↗** opens each official IEEE file in your browser for manual **Import CSV** when automated requests are blocked by IEEE or your corporate network.
- **Clipboard** keeps session-only history; monitoring still depends solely on menu visibility.
- Window positions for Normal and Mini are stored **separately**; notes, commands and shortcuts continue sharing the same underlying local data.

Mini Mode is included in **v1.28** on `main`. The two views share the same notes, commands and shortcuts. Window positions are saved independently; Windows display-scaling behavior may vary by device.

### Single-instance protection — v1.28

On Windows, normal launches of Pocket now enforce **one running copy per signed-in Windows session** (including launches from different folders, `run.bat`, or the packaged EXE). Launching Pocket a second time **opens the existing window** instead of starting another tray icon or another process that could overwrite notes. The existing instance keeps its current notes, settings and position.

This uses Windows named mutex and event objects locally, with **no internet connection, background service, registry changes or lock file**. It releases automatically on app exit or process termination. The optional `--preview` mode is excluded so development screenshots/tests can run separately. This safeguard prevents duplicate app processes; it does **not** prevent a separate text editor from changing files in the background.

Single-instance protection is included in v1.28. A second launch activates the existing Pocket window instead of starting another process. The native Windows tray integration has been tested by a user; different Windows configurations may still vary.

### Personalize the workspace

**Settings (⚙)** shows or hides tool menus without deleting their underlying saved data. When **Clipboard** is included in the visible menus, Pocket monitors new copied text while running—even when its window is hidden in the tray. Hide Clipboard to stop monitoring; there is **no second enable/disable switch**. Additional visible tools are accessible under **MORE**.

| Feature | How it works |
|:---|:---|
| **Six color themes** | Click the **pocket logo** to choose Blue, Dark Blue, Black, Red, Green or Purple. Pocket updates the window colors, in-app logo and tray icon, then remembers your choice. |
| **Your own popup shortcut** | Click the shortcut label directly beneath **Pocket** to select Ctrl/Alt/Shift/Win modifiers and a key. Default: **Ctrl + Shift + \***. If Windows cannot register a new combination, the previous working shortcut is retained. |
| **Move and remember** | Drag the header to move the popup. The position is saved and restored. Right-click the header → **Reset window position**. |
| **PIN mode** | Keep Pocket visible when you switch to another app — useful for copying information and dragging shortcuts. |
| **System tray** | Click the tray icon to show/hide Pocket. The close button hides the popup; it doesn't erase your notes. |
| **Scheduled note reminders** | On an individual note, choose **Notify me…**, set a local date and time, and receive a Windows tray notification. Clicking the notification is designed to reopen that note. Overdue, unsent reminders are checked on the next launch. |
| **Menu visibility** | Show/hide individual tool tabs under Settings, without removing any saved data. |

**Note on icons:** The live window and system-tray icons change with your selected theme. The compiled EXE retains its **blue embedded icon**, and Windows can cache desktop/taskbar shortcut artwork.

### Scheduling a note reminder

1. Open **Notes** and select the note you want.
2. Check **Notify me** next to the note details, or right-click the note in the list and choose **Notify me…**.
3. Enter the **date** as `YYYY-MM-DD` and the **time** as `HH:MM` (24-hour, using your computer's local time); choose **Save reminder**.
4. Keep Pocket running in the Windows system tray. At the scheduled time, Pocket sends a Windows notification with the note title and a short text preview.

Uncheck **Notify me** to cancel the reminder. To reschedule, select the reminder's date/time or use **Change notification time…** in the note menu. Reminders are one-shot and their delivery state is stored in `data.json` to avoid repeatedly notifying after a restart.

> **Limitations:** Pocket does not register a system-level background alarm. It must be running to deliver a notification on time; if closed, it checks overdue reminders when restarted. Notifications use Windows tray balloon APIs rather than a full Windows App SDK toast integration. Appearance, click behavior, and delivery depend on Windows notification settings and should be tested on Windows.

### Clipboard behavior and privacy

- **Show Clipboard in Settings** → Pocket starts recording newly copied text, including while minimized to the system tray.
- **Hide Clipboard in Settings** → Pocket stops collecting new entries. Hiding the tab does **not** clear the current in-memory list.
- Clipboard history is **session-only**: it is not written to `data.json` and disappears when Pocket exits. Text copied before Pocket starts is not recovered from Windows clipboard history.
- Copying passwords, API keys, or other sensitive text can cause them to appear in clipboard history during that session. Use **Clear all** and hide Clipboard when appropriate. Pocket does not automatically identify secret content.



## Getting started

**Recommended:** [Download the portable ZIP](https://github.com/Dovshmi/Pocket/releases/download/v1.28/Pocket-Portable-v1.28.zip), extract the entire folder, close any currently running Pocket instance, and launch `PocketDesk.exe`. Python is **not** required. Personal data stays in the portable folder’s `data/` directory.

### Run from source — developer setup

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

1. Open **Notes**, create a note and try **Notify me…** to schedule a reminder.
2. Open **Settings (⚙)** and choose which menus appear. Add or hide **Clipboard** to start or stop text monitoring.
3. Open **Shortcuts** and add a website or folder, then try the live search.
4. Click the **pocket logo** to change themes, or click the shortcut label under Pocket to customize the global hotkey.
5. Open **Subnet** and calculate `192.168.1.10/24`, or use **Commands → Backup ▾** to save a manual command-library backup.

## Pocket Portable

Pocket Portable is a **Windows ZIP** containing `PocketDesk.exe`, its dependencies
and a `portable.flag` marker. Extract the ZIP and run the EXE without installing
Python on the destination computer. The marker switches **all application data**
(notes, reminders, shortcuts, settings, cache, icons, Notepad sync and commands)
to the adjacent `data/` directory. If that folder is not writable, startup
shows an error instead of silently storing information in the host's AppData.

**Download:** [Pocket Portable v1.28](https://github.com/Dovshmi/Pocket/releases/tag/v1.28). Extract the entire ZIP and launch `PocketDesk.exe`; do not execute it inside the compressed ZIP.

To build the portable ZIP on a Windows **development** machine (Python + internet
may be needed on the build machine), run `build-portable.bat`. It uses PyInstaller
`--onedir` and then `package_portable.py`, producing
`dist/Pocket-Portable-v1.28.zip`.

The archive contains only **public sample commands**. A first launch creates
`data/commands.json` from that example. **It never bundles** the tracked
`commands/commands.json`, personal notes, or backups. To migrate personal
data, copy your own files manually **after extracting**, with Pocket closed,
and do not overwrite existing files without reviewing them.

Portable and standard installations share the same single-instance lock within
a Windows sign-in session: close one before opening the other. Portable mode
does not bypass workplace policy or application allowlisting; use it only on
computers on which you are permitted to run it.

> **Security and compatibility:** The Windows EXE is not code-signed. Windows SmartScreen or organizational policies may block it; do not override workplace controls. The source and automated tests are available in this repository. Launching on every possible clean Windows configuration has not been independently verified.

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
> **Build-script distinction:** `build-exe.bat` can embed a local `commands/commands.json`, which may contain private commands. **Do not distribute its output without auditing that file.** For public distribution use `build-portable.bat`: the [official v1.28 ZIP](https://github.com/Dovshmi/Pocket/releases/tag/v1.28) bundles only the public example library.

**Packaging caveat:** Native Windows tray interaction, hotkey registration, icon refresh and multi-monitor behavior should be tested on a Windows machine before distributing a build. Passing headless tests alone does not validate those integrations.

## Files, settings and privacy

When running from source without `portable.flag`, Pocket saves user data under:

```text
%APPDATA%\PocketDesk\
├── data.json            # Notes/reminders, shortcuts, theme, hotkey, window position, menu preferences
├── vendors.json         # Cached or imported IEEE vendor data
├── icons\               # Locally generated color icon variants (PNG / ICO)
├── notepad_exports\     # Older, one-off .txt snapshots of notes
└── notepad\             # Stable working .txt files for Notepad synchronization
```

- **Portable data:** with `portable.flag` beside the EXE, notes, settings, vendor cache, icons, Notepad sync and the writable `commands.json` are stored in `Pocket-Portable/data/`. Standard source mode keeps its existing AppData behavior.
- **Local-first:** no account, hosted database or synchronization service is required.
- **Not encrypted:** notes, scheduled reminders, phone numbers and command libraries are stored as **plain-text JSON**. Do not store passwords or private keys there.
- **Clipboard history:** text is held in memory only and is cleared when Pocket exits. Turning off the Clipboard menu stops future capture, not the Windows system clipboard itself.
- **Notepad synchronization:** **Open in Notepad** opens a stable local working file. Saving in Notepad updates the Pocket note while Pocket is running (checked approximately every 1.2 seconds). If both editors changed the note, Pocket prompts before replacing content, and preserves a recovery copy when the Pocket version is selected. Older one-off exports remain separate and are not synchronized.
- **Network activity:** TCP checks contact only the specified target. Registry downloads retrieve IEEE vendor data when requested. Pocket doesn't send notes to a lookup service.
- **Authorization:** only scan systems you own or are authorized to test. A port timeout does not prove a port is closed.
- **MAC limitations:** an OUI indicates a registered vendor prefix, not proof of the exact device manufacturer or owner. IEEE may block scripted requests (such as HTTP 403/418/429), and work PCs may block the IEEE domain; Pocket now shows the underlying error and provides **Get CSV ↗ → Import CSV** as a manual alternative. Downloading requires network access only when requested.

### CLI command library

The Commands tab uses **one writable JSON library**: `data/commands.json` in Portable Mode, or the resolved sidecar/AppData library in Standard Mode. Commands may be searched by machine and category, edited, copied, favorited, or deleted. Edits are saved atomically. **No automatic backup is created on save, edit, delete, or migration.** To make a backup, open **Commands → Backup ▾ → Create new backup**; use **Use existing backup** to choose a previously saved JSON file. Restoring replaces the active command library, so make a manual backup first if you need to preserve current changes. See [the example format](commands/example_commands.json).

> [!WARNING]
> **Public-repository review needed:** A command library is currently checked into this public repository, including a second copy at `Pocket_Commands_One_Library/commands/commands.json`. Review both copies for internal device names, infrastructure details, or other sensitive material before sharing. The `.gitignore` rule does **not** retroactively remove committed files. Do not commit secrets or workplace-only command collections.

The local application does not upload command edits automatically; GitHub publishing is a separate action.

> **Packaging caution:** Review the source library before building an EXE: a local `commands/commands.json` may be bundled inside it. Do not distribute a build containing private commands.

## Project structure

```text
Pocket/
├── app.pyw                 # Desktop UI, notes, tabs and tray
├── note_sync.py            # Notepad working-file sync and conflict backups
├── mini_layout.py          # Mini geometry, layout preferences and command paging
├── single_instance.py      # Windows mutex and activation-event protection
├── portable_storage.py     # Portable folder-local data paths
├── native_bidi.py          # Windows native right-to-left note editor
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
├── build-exe.bat           # Optional standalone EXE for local/private use
├── build-portable.bat      # Public Windows ZIP build
├── package_portable.py     # Package clean portable ZIP from onedir output
├── docs/images/            # Illustrated v1.28 interface previews
├── .github/workflows/      # Tests and release automation
├── test_*.py               # Unit tests
└── smoke_*.py              # Optional GUI smoke checks
```

**Stack:** Python 3.10+, Tkinter/ttk, native Win32 APIs via `ctypes`, Pillow, `tkinterdnd2` and PyInstaller.

**Release:** [Pocket v1.28](https://github.com/Dovshmi/Pocket/releases/tag/v1.28) includes a GitHub Actions-built portable ZIP and SHA256 checksum; the Windows EXE itself is **not code-signed**.

## Version history

> **Current release:** v1.28 on `main`, with a portable Windows ZIP from [Releases](https://github.com/Dovshmi/Pocket/releases/tag/v1.28). Mini Mode remains available in Settings, and the existing Normal Mode continues to work.

Development milestones shown below are drawn from repository commits and feature implementations; they are **not** a claim that each intermediate version has a separate downloadable GitHub Release.

| Version | Date | Highlights |
|:---|:---|:---|
| **v1.28** | 2026-10-30 | Portable Windows ZIP with self-contained EXE and folder-local data, safe example command library, single-instance activation and Normal Notes focus correction; Windows/Linux regression tests and build workflows. |
| **v1.27** | 2026-10-30 | Settings-controlled Mini Mode with icon tabs; one-command carousel and keyboard navigation; compact Notes/Shortcuts; per-mode positions; scrollable Normal/Mini tools; four-row Normal Commands results with fixed header; improved IEEE CSV fallback and filter-wheel behavior. |
| **v1.26** | 2026-10-29 | Unified Windows Unicode editor for LTR/RTL (fixes mixed-language right-click crash), Notepad save-to-Pocket synchronization with conflict handling, and direct Copy buttons for shortcuts. |
| **v1.25** | 2026-10-28 | Clipboard capture now follows menu visibility (no separate toggle). Added per-note one-shot reminders with local date/time scheduling, persistent delivery state and Windows tray notification handling. |
| **v1.24** | 2026-10-28 | Added Clipboard history, Settings, menu visibility controls, tray notification support and manual-only Commands backup/restore. |
| **v1.23** | 2026-10-28 | Consolidated commands into a single writable local `commands.json` library, with optional machine names stored in the same file. |
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

The project includes tests for data storage and migration, theme settings, generated icons, configurable hotkeys, shortcut filtering, subnets, command management, clipboard preferences, reminder scheduling, note actions, Mini Mode, scroll behavior and network utilities.

GUI smoke scripts are provided separately (see `smoke_*.py`) and need a functioning display. **The repository includes Windows/Linux unit-test workflows; automated checks do not replace interactive Windows GUI testing.** The new command coverage tests are source-level checks, not proof that every command works on every vendor model and firmware.

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
