<div align="center">

<img src="assets/app.png" width="96" alt="Pocket — hand-in-pocket app icon" />

# Pocket

**One shortcut. Your entire Windows toolbox.**

A compact, local-first desktop workspace for network operations, support teams, and everyday productivity.

[![Source version](https://img.shields.io/badge/Main%20source-v1.42.0-3273DC?style=flat-square)](https://github.com/Dovshmi/Pocket/tree/main)
[![Stable download](https://img.shields.io/badge/Stable%20Windows-v1.42.0-6755D8?style=flat-square)](https://github.com/Dovshmi/Pocket/releases/tag/v1.42.0)
![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square&logo=windows&logoColor=white)
![Offline-first](https://img.shields.io/badge/Offline--first-Yes-14866D?style=flat-square)
[![License](https://img.shields.io/badge/License-GPL--3.0-556276?style=flat-square)](LICENSE)

**[Download Portable ZIP v1.42.0](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/Pocket-Portable-v1.42.0.zip)** · **[Standalone EXE v1.42.0](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/Pocket-v1.42.0.exe)** · [Checksums](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/SHA256SUMS.txt) · [All releases](https://github.com/Dovshmi/Pocket/releases)

<sub>Official v1.42.0 Windows release · Portable ZIP + standalone EXE · Previous v1.40.0 downloads are preserved.</sub>

</div>

---

<div align="center">
  <img src="docs/images/pocket-v140-real/dashboard_home.png" alt="Pocket v1.40.0 real Windows Dashboard overview with workspace navigation" width="900" />

  <sub><strong>Pocket Dashboard · v1.40.0</strong> — historical capture from automated Windows GUI tests with sample data.</sub>
</div>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#whats-new-in-v1420">What's new</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#privacy--connectivity">Privacy</a> ·
  <a href="#version-history">Changelog</a>
</p>

## Why Pocket?

Pocket keeps the small tools you reach for all day **in one tray application**. Open it when needed, choose Normal, Mini, Dashboard, or Extra Mini, and return to work. Window placement, theme, menu visibility, icon order, and your last tool are saved locally.

- **Local-first:** Notes, CLI references, subnet math, reminders, clipboard tools, backups, and offline Excel database lookups work without a constant internet connection.
- **Fast to reach:** Tray access, configurable global hotkey, quick search, draggable Mini icons, and optional nine-slot Numpad text shortcuts.
- **Built for real workflows:** TCP and MAC diagnostics, Excel record lookup, and optional unsent Outlook SOC drafts.
- **Opt in to remote checks:** DashDash is used only when you choose the remote source and run a check. Local tools never require a Pocket account.

## What's new in v1.42.0

**Command Palette, adaptive window sizes and smarter network tools.** This official release includes both the v1.41 workspace improvements and the v1.42 updates. [Full release notes](docs/releases/v1.42.0.md).

| Area | Improvements |
| :--- | :--- |
| **Command Palette · Ctrl+K** | Search tools, notes, shortcuts and CLI references; invoke internal actions, recognize IP/MAC/CIDR input and prepare network checks. Opens above Pocket and restores focus on close. |
| **Adaptive layouts · v1.41** | Resize between Mini, Normal and Dashboard, save named size profiles and reorder responsive navigation. Extra Mini stays fixed. |
| **TCP ports** | Mixed ranges and individual ports (e.g. `80,554,2079-2084,22,21`), green OPEN/red unsuccessful rows and a thin progress bar. |
| **MAC Vendor** | Compact IEEE header and collapsible vendor counts, include/exclude filtering and summary copy. |
| **Extranet** | Offline Database mode opens by default; Local workbook mode remains available. |
| **Settings & Clipboard** | Compact controls, responsive menu ordering, backup of window profiles and unobtrusive resize edges. |

### Command Palette examples

With Pocket open, press **Ctrl+K**, type an action or search term, use Up/Down and Enter, and close with Esc. A leading `>` restricts results to internal commands.

| Input | Action |
| :--- | :--- |
| `> new note` | Create a note |
| `> theme black` / `> size mini` | Change appearance or size |
| `> clipboard pause` | Pause clipboard capture |
| `> port 192.168.1.1 80,443,2079-2084` | Prepare a port check |
| `> mac 00:00:0C:12:34:56` | Prepare a MAC lookup |
| `> subnet 192.168.10.0/26` | Calculate a subnet |
| `> extra 10.0.0.1` | Search Extranet |
| `> cli cisco show vlan` | Search local CLI references |

No shell execution or AI service is involved. Network checks require an explicit run. Ctrl+K is internal to Pocket, not a system-wide shortcut.

> [!NOTE]
> Automated Windows/Linux checks use synthetic data. Protected Excel/Outlook integration, enterprise proxy access and approval for unencrypted local storage require workstation-specific acceptance tests.

## Screenshots

**Historical v1.40.0 Windows captures** (not screenshots of the new v1.42 interface), taken by the automated GUI smoke tests with a synthetic user profile. These are not mockups and do not contain customer workbooks or private commands. UI contents and window arrangements may vary by selected mode.

<div align="center">
<table>
<tr>
<td width="50%" align="center"><img src="docs/images/pocket-v140-real/dashboard_notes.png" alt="Pocket v1.40 Dashboard Notes editor" width="440" /><br /><strong>Notes</strong></td>
<td width="50%" align="center"><img src="docs/images/pocket-v140-real/dashboard_commands.png" alt="Pocket v1.40 searchable command library" width="440" /><br /><strong>Command Helper</strong></td>
</tr>
<tr>
<td align="center"><img src="docs/images/pocket-v140-real/dashboard_ports.png" alt="Pocket v1.40 TCP port diagnostics" width="440" /><br /><strong>TCP Port Checker</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/dashboard_mac.png" alt="Pocket v1.40 MAC lookup" width="440" /><br /><strong>MAC Vendor Lookup</strong></td>
</tr>
<tr>
<td align="center"><img src="docs/images/pocket-v140-real/dashboard_clipboard.png" alt="Pocket v1.40 Clipboard history" width="440" /><br /><strong>Clipboard Manager</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/dashboard_settings.png" alt="Pocket v1.40 themes and show-hide Settings" width="440" /><br /><strong>Settings</strong></td>
</tr>
</table>
</div>

<details>
<summary><strong>More screenshots — Mini, Shortcuts, Subnet & Extra Mini</strong></summary>

<br />

<div align="center">
<table>
<tr>
<td align="center"><img src="docs/images/pocket-v140-real/mini_notes.png" alt="Pocket compact Mini Notes view" width="240" /><br /><strong>Mini Notes</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/mini_links.png" alt="Pocket compact Mini Quick Shortcuts view" width="240" /><br /><strong>Mini Shortcuts</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/mini_commands.png" alt="Pocket compact Mini Commands view" width="240" /><br /><strong>Mini Commands</strong></td>
</tr>
<tr>
<td align="center"><img src="docs/images/pocket-v140-real/dashboard_subnet.png" alt="Pocket IPv4 subnet calculator" width="240" /><br /><strong>Subnet Calculator</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/mini_settings.png" alt="Pocket Mini Settings" width="240" /><br /><strong>Mini Settings</strong></td>
<td align="center"><img src="docs/images/pocket-v140-real/extra_mini.png" alt="Pocket Extra Mini launcher with custom tiles" width="240" /><br /><strong>Extra Mini launcher</strong></td>
</tr>
</table>
</div>

</details>

<sub>Screenshot provenance: [v1.40.0 Windows CI run](https://github.com/Dovshmi/Pocket/actions/runs/45080242747). Older [v1.30 screenshots](docs/images/pocket-v130-real) remain available for historical comparison. The Excel/SQLite module is documented in its [feature guide](docs/EXTRA_EXCEL_LOOKUP.md); it is not shown in the gallery above.</sub>

## Features

| Tool | What you can do | Connection |
| :--- | :--- | :--- |
| **Notes** | Save title, phone, text, creation time, pinned notes; duplicate, search and open in Windows Notepad. | Offline |
| **Reminders** | Schedule stand-alone or Note-linked alerts, snooze, mark complete and retain responses locally. | Offline |
| **Commands Helper** | Search command references by device/category, use Smart Templates, edit and copy CLI; no command execution. | Offline |
| **Quick Shortcuts** | Organize URLs, files, folders and apps; drag/reorder; open Excel workbooks intelligently. | Only if opening web links |
| **TCP Port Checker** | Check up to 16 distinct TCP ports including ranges, manage favorites, view color-coded progress/results and export CSV. | Local or opt-in DashDash |
| **MAC Vendor Lookup** | Resolve locally or via optional DashDash; view vendor counts, filter and copy summary. | Local or opt-in DashDash |
| **Subnet Calculator** | Calculate IPv4 CIDR, masks, wildcard, host ranges, network and broadcast addresses. | Offline |
| **Clipboard Manager** | Keep text and image history, search, pin, manage retention and use nine Quick Slots. | Offline |
| **Extranet · Excel** | Default offline SQLite search, optional Local workbook mode/manual Sync, selected-row details and Outlook SOC draft. | Local / offline index |

### A few useful workflows

**Excel → matched customer → SOC draft.** In Extra, browse to an authorized workbook, search across worksheets, inspect the selected record and choose **Outlook · SOC**. Pocket prepares a draft only; it **never sends the email**. The database mode is independent of Excel once an index has been created and loaded.

**Selected text → Quick Slot → paste later.** Save text to one of nine numbered slots and insert it into another application using configurable Numpad shortcuts. Slot content is deliberately **excluded from portable backups**.

**CLI lookup → Smart Template → copy.** Filter by machine or category, fill supported placeholders such as `{{IP}}`, then copy the command. Pocket does not run network commands on your behalf.

**One window, several layouts.** Normal keeps the classic compact workflow; Mini sits beside other applications; Dashboard provides a wider overview; Extra Mini offers a customizable tile launcher. Resize the working window to switch layouts, save named profiles, or use Extra Mini independently. Choose any of six themes: Blue, Dark Blue, Black, Red, Green, or Purple.

Guides: [Quick Slots](docs/QUICK_SLOTS.md) · [Backup & Restore](docs/BACKUP_RESTORE.md) · [Excel & SOC](docs/EXTRA_EXCEL_LOOKUP.md) · [Windows proxy](docs/WINDOWS_PROXY.md)

## Installation

### Windows stable — v1.42.0

| Portable ZIP <sub>(recommended)</sub> | Standalone EXE |
| :--- | :--- |
| **[Pocket-Portable-v1.42.0.zip](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/Pocket-Portable-v1.42.0.zip)** | **[Pocket-v1.42.0.exe](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/Pocket-v1.42.0.exe)** |
| Extract the full archive, then run `Pocket-Portable/PocketDesk.exe`. Keep its `_internal/` folder beside it. | Run the single EXE directly. |
| Local data: `Pocket-Portable/data/`. | Local data: `%APPDATA%\PocketDesk\`. |

No Python installation is needed for either Windows binary. Both downloads are built from the official **v1.42.0** source. Verify them with [SHA-256 checksums](https://github.com/Dovshmi/Pocket/releases/download/v1.42.0/SHA256SUMS.txt). [v1.40.0](https://github.com/Dovshmi/Pocket/releases/tag/v1.40.0) remains available for rollback.

**Upgrading a portable installation:** fully exit Pocket (including the tray process), back up the old `data/` folder, extract the new ZIP into a **new** folder and copy only your user data across. Never mix `_internal/` folders from different versions. You can also use **Settings → Backup & Restore** to transfer selected data.

> [!IMPORTANT]
> Windows binaries are **not code-signed**. Use them on managed machines only when permitted by your organization. Do not bypass workplace application controls. See [workplace setup notes](docs/WORKPLACE_PORTABLE.md).

### Run from source

Tested in CI with Python **3.11 and 3.13**, on Windows and Linux (Windows-specific Office features require Windows).

```powershell
git clone https://github.com/Dovshmi/Pocket.git
cd Pocket
py -3 -m pip install -r requirements.txt
py -3 app.pyw
```

## Productivity shortcuts

| Action | Default |
| :--- | :--- |
| Show/hide Pocket | Tray icon or configurable global hotkey |
| Command Palette (Pocket open) | `Ctrl+K` |
| Close Command Palette | `Esc` |
| Find within Commands | `Ctrl+F` |
| New Note | `Ctrl+N` |
| Save | `Ctrl+S` |
| Save selected/clipboard text to Quick Slot 1–9 | `Ctrl+Alt+Win+Numpad1–9` |
| Paste a saved Quick Slot | `Ctrl+Alt+Numpad1–9` |

Quick Slot shortcuts use **Num Lock ON**. Their modifier combinations and paste behavior can be configured in Settings. [Full Quick Slots reference](docs/QUICK_SLOTS.md).

## Privacy & connectivity

Pocket does not require an account, cloud sync, or permanent internet access. Most tools operate locally; **remote diagnostics are an explicit choice**.

| Feature | Local behavior / privacy notes |
| :--- | :--- |
| **Notes, reminders, shortcuts & settings** | Stored in the local Pocket profile (`data.json`). |
| **CLI library** | Custom commands are local. Public downloads include only sanitized example commands. |
| **Clipboard** | RAM-only history by default; optional local Text/Images DATABASE is opt-in and stores readable text/PNG files. |
| **Quick Slots** | Stored locally and **excluded** from portable backup exports. |
| **Excel Extra** | Local workbook read-only lookup. Offline SQLite is created/refreshed **only when Sync is pressed**. SQLite stores readable data and is **not encrypted**. |
| **Backup & Restore** | Manual, selective local ZIP backup; restore preview with Merge/Replace and safety snapshot. ZIP files are **not encrypted**. |
| **MAC vendor data** | Local IEEE cache unless an explicit remote lookup is requested. |
| **TCP checks** | Local checks run from your PC. Opt-in DashDash checks run **from Vercel**, not your workstation, and support public IPv4 targets. |

For authorized remote checks, Pocket can use the configured Windows proxy/PAC with HTTPS certificate checks intact. Switching a source does not silently run a network scan. Avoid submitting confidential customer/infrastructure targets to remote services.

> [!CAUTION]
> Pocket's offline Excel index, clipboard DATABASE, and backup ZIPs can contain **unencrypted local copies of sensitive information**. Only use these features with approved datasets and storage under your organization's policies. Do not commit workbooks, SQLite files, backups, passwords, or customer data to a public repository.

[Clipboard storage & retention](docs/CLIPBOARD_DATABASE.md) · [Proxy/PAC details](docs/WINDOWS_PROXY.md) · [Backup details](docs/BACKUP_RESTORE.md)

## Version history

| Version | Highlights | Distribution |
| :--- | :--- | :--- |
| **v1.42.0 — latest stable** | Command Palette, smart inputs and internal actions, TCP ranges/colors/progress, MAC counts/filtering, Database-first Extranet. | **Official Windows ZIP / EXE** |
| **v1.41** | Adaptive window sizing, named profiles, responsive/reorderable navigation and compact Clipboard. | Included in v1.42.0 |
| **v1.40.0** | Extra Excel / SQLite lookup, Outlook SOC draft, smart Excel shortcut reuse, movable Mini menus, compact Show / Hide, improved scrolling. | Previous stable release |
| **v1.39.9** | Stand-alone and Note-linked Reminders, snooze, response capture, compact Reminder navigation. | Previous stable release |
| **v1.39.1–v1.39.8** | Quick Slots paste, save, history preservation, settings and Windows notice refinements. | Previous stable releases |
| **v1.39.0** | Selective Backup & Restore, nine Quick Slots, shortcut recorder and Settings reset. | Previous stable release |
| **v1.38.0** | Clipboard DATABASE improvements, Notes/Notepad sync, keyboard-layout repair and proxy support. | Previous stable release |
| **v1.34–v1.37** | Native Windows input, foldered Shortcuts, screenshot history, better networking and UI controls. | Earlier releases |

All older releases are preserved. See **[full release notes](RELEASE_NOTES.md)**, [individual release notes](docs/releases), and [GitHub Releases](https://github.com/Dovshmi/Pocket/releases).

## Development & contributing

**Stack:** Python, Tkinter/ttk, Windows APIs and Office COM integration, Pillow, `tkinterdnd2`, optional `openpyxl`/`xlrd` Excel readers, SQLite and PyInstaller.

```powershell
# Run unit tests
py -3 -m unittest discover -s tests -p "test_*.py" -v

# Build the Windows distributions
.\build-portable.bat
.\build-exe.bat
```

GitHub Actions runs Windows/Linux unit and GUI checks and Windows portable runtime smoke tests. Synthetic data is used for automated UI screenshots; protected enterprise Excel, Outlook and local data-policy acceptance must be tested separately on authorized workstations.

[Repository structure](docs/REPOSITORY_LAYOUT.md) · [Open an issue](https://github.com/Dovshmi/Pocket/issues) · [v1.42 release notes](docs/releases/v1.42.0.md)

---

<div align="center">

**Pocket — small tools, one workspace.**

Made by Rony Shmidov · [GPL-3.0](LICENSE) · Windows 10/11

</div>
