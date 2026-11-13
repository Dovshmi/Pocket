<div align="center">

<img src="assets/app.ico" alt="Pocket official hand-and-pocket app icon" width="112" height="112" />

# Pocket

**Your everyday Windows toolbox. One shortcut away.**

A lightweight, local-first toolkit for NOC/SOC work, network troubleshooting, notes, and everyday productivity.

[![Release](https://img.shields.io/badge/Stable-v1.33.1-6755D8?style=for-the-badge)](https://github.com/Dovshmi/Pocket/releases/tag/v1.33.1)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Offline-first](https://img.shields.io/badge/Offline--first-Yes-14866D?style=for-the-badge)
[![License](https://img.shields.io/badge/License-GPL--3.0-556276?style=for-the-badge)](LICENSE)

**[Download Portable ZIP](https://github.com/Dovshmi/Pocket/releases/download/v1.33.1/Pocket-Portable-v1.33.1.zip)** ·
**[Download Standalone EXE](https://github.com/Dovshmi/Pocket/releases/download/v1.33.1/Pocket-v1.33.1.exe)** ·
**[All Releases](https://github.com/Dovshmi/Pocket/releases)**

</div>

---

Pocket runs from the Windows system tray and opens on demand. It brings seven practical tools together in **Normal, Mini, Dashboard, and Extra Mini** layouts, with six color themes and customizable visible menus. Notes, CLI references, subnets, and clipboard history work without an internet connection; network access is initiated only when you request it.

> [!NOTE]
> **v1.33.1:** DashDash MAC lookups and remote TCP checks now support Windows-managed corporate **Proxy/PAC/WPAD** settings, including environments where a browser can reach HTTPS but direct TCP/443 is restricted. Local mode remains the default. [Release notes](RELEASE_NOTES.md) · [Windows proxy details](docs/WINDOWS_PROXY.md).

## Screenshots

These are **real Pocket screenshots from Windows GUI tests** (not mockups). The images were captured in **v1.30.0**; later releases refined some layouts. See the [latest UI-test artifacts](https://github.com/Dovshmi/Pocket/actions/workflows/mini-checks.yml) for additional captures.

<div align="center">
<img src="docs/images/pocket-v130-real/dashboard_home.png" width="850" alt="Real Pocket Dashboard home" />

**Dashboard**

<table>
<tr>
<td align="center"><img src="docs/images/pocket-v130-real/dashboard_notes.png" width="420" alt="Pocket Dashboard Notes editor" /><br /><strong>Notes</strong></td>
<td align="center"><img src="docs/images/pocket-v130-real/dashboard_commands.png" width="420" alt="Pocket Dashboard CLI Commands" /><br /><strong>Commands</strong></td>
</tr>
<tr>
<td align="center"><img src="docs/images/pocket-v130-real/normal_ports.png" width="290" alt="Pocket TCP Port Checker" /><br /><strong>TCP Port Checker</strong></td>
<td align="center"><img src="docs/images/pocket-v130-real/extra_mini.png" width="290" alt="Pocket Extra Mini launcher" /><br /><strong>Extra Mini</strong></td>
</tr>
</table>
</div>

<details>
<summary><strong>View more real app screenshots</strong></summary>

| Normal Notes | MAC Vendor Lookup | Mini Commands |
|:---:|:---:|:---:|
| <img src="docs/images/pocket-v130-real/normal_notes.png" width="240" alt="Normal Notes" /> | <img src="docs/images/pocket-v130-real/normal_mac.png" width="240" alt="MAC Lookup" /> | <img src="docs/images/pocket-v130-real/mini_commands.png" width="240" alt="Mini Commands" /> |

| Subnet Calculator | Clipboard | Dashboard Settings |
|:---:|:---:|:---:|
| <img src="docs/images/pocket-v130-real/dashboard_subnet.png" width="240" alt="Subnet Calculator" /> | <img src="docs/images/pocket-v130-real/dashboard_clipboard.png" width="240" alt="Clipboard History" /> | <img src="docs/images/pocket-v130-real/dashboard_settings.png" width="240" alt="Settings" /> |

</details>

## Tools at a glance

| Tool | What it does | Connectivity |
| :--- | :--- | :--- |
| **Notes & reminders** | Titled notes with phone numbers, creation times, RTL/LTR editing, pin/duplicate, Notepad integration, and native Windows reminders | Offline |
| **Commands Helper** | Searchable CLI references by device/topic; edit, favorite, fill validated Smart Templates such as `{{IP}}`, then copy | Offline |
| **Quick Shortcuts** | Save, search, and open websites, local files, and folders | Online only when you open a web link |
| **TCP Port Check** | Check up to **16 TCP ports** per run, with favorites, last-check suggestions, status sorting, and CSV export | Local or optional DashDash |
| **MAC Vendor Lookup** | Search cached IEEE registrations (MA-L, MA-M, MA-S, IAB), import CSV, or query DashDash | Local or optional DashDash |
| **Subnet Calculator** | IPv4 CIDR, masks, wildcard, network/broadcast, usable hosts, and subnet splitting | Offline |
| **Clipboard Manager** | Search, pin, copy, remove, and pause session-only clipboard history; optional sensitive-text filter | Offline |

**Commands are references, not scripts:** Pocket never executes a saved CLI command. Smart Templates fill placeholders before copying; manual command backups are created **only when you choose Backup**.

**Reminders** use Windows tray notifications while Pocket is running or minimized to the tray, with overdue unsent reminders checked at the next launch. Hiding the Clipboard menu also stops clipboard monitoring; clipboard history is never saved to disk.

## Local vs. DashDash network checks

| Mode | Where the network check runs | Supported targets |
| :--- | :--- | :--- |
| **Local (default)** | On your Windows computer | TCP checks to reachable IPv4/IPv6, including private networks; MAC lookup from your local IEEE cache |
| **DashDash (opt-in)** | Pocket sends an HTTPS request to the DashDash API; the remote TCP test runs on Vercel | **Public IPv4 only** for TCP checks, up to 16 ports; remote MAC lookup up to 100 addresses |

- **Windows corporate networks:** for explicitly requested DashDash checks, Pocket uses the signed-in user's approved Windows proxy configuration, resolves PAC/WPAD for the destination, and sends HTTPS through the native Windows stack. There are no hard-coded workplace proxy settings, and certificate validation is not disabled.
- **No background scans:** switching modes does not run a check. Remote requests occur only after clicking **Run TCP check** or **Check vendors**. Offline tools do not depend on DashDash.
- **Know the source:** a DashDash TCP result measures reachability **from Vercel**, not from your work PC; use Local mode for internal networks. The DashDash API is public and has no Pocket account-level authentication. Only check targets you are authorized to test, and do not submit confidential customer or infrastructure data.

[How Windows Proxy/PAC works](docs/WINDOWS_PROXY.md)

## Window layouts and everyday controls

| Layout | Designed for |
| :--- | :--- |
| **Normal** | Everyday menu-based work |
| **Mini** | Compact workspace alongside other applications |
| **Dashboard** | Wider side-by-side tools and editing |
| **Extra Mini** | Optional quick-action launcher with customizable tiles and pages |

Pocket remembers window placement and supports **Blue, Dark Blue, Black, Red, Green, and Purple** themes. Pin the popup to keep it open, or close it to hide it in the tray.

| Action | Shortcut / control |
| :--- | :--- |
| Show or hide Pocket | Tray icon or configurable global hotkey |
| Quick Search across enabled tools | `Ctrl+K` |
| Find commands while in Commands | `Ctrl+F` |
| New note | `Ctrl+N` |
| Save | `Ctrl+S` |
| Fully quit | Tray icon → **Exit** |

## Download and use

### Portable ZIP — recommended for a work PC

1. Download **[Pocket-Portable-v1.33.1.zip](https://github.com/Dovshmi/Pocket/releases/download/v1.33.1/Pocket-Portable-v1.33.1.zip)**.
2. **Extract the whole archive** into a writable local folder. Do not run the EXE inside the ZIP.
3. Launch `Pocket-Portable/PocketDesk.exe` and leave the `_internal/` folder beside it.
4. Choose a window layout and theme in Settings.

No Python installation is required. The portable version stores personal data under `Pocket-Portable/data/` beside the EXE. For upgrades, fully exit Pocket, back up `data/`, extract the new release into a **different** folder, and copy your personal `data/` folder over. Never mix old and new `_internal/` runtime files.

### Standalone EXE

Download **[Pocket-v1.33.1.exe](https://github.com/Dovshmi/Pocket/releases/download/v1.33.1/Pocket-v1.33.1.exe)** and run it directly. It stores its user data in `%APPDATA%\\PocketDesk\\` rather than beside the EXE.

> [!IMPORTANT]
> Releases are **unsigned**. Corporate application-control, antivirus, or proxy policies may block the program. Use Pocket only where authorized; do not disable workplace security controls. [Portable workplace troubleshooting](docs/WORKPLACE_PORTABLE.md).

## Privacy and data

Pocket has **no mandatory account, cloud sync, or continuous internet requirement**.

| Data | Storage |
| :--- | :--- |
| Notes, settings, reminders, shortcuts, launcher setup | Local `data.json` |
| Personal CLI commands and Smart Template metadata | Local `commands.json` |
| IEEE vendor cache | Local `vendors.json` |
| Clipboard history | **RAM only**; cleared when Pocket exits |
| Recoverable settings snapshot | Local `data-recovery.json` |

Public Windows releases contain the **sanitized example command library only**—not private commands, notes, passwords, customer information, or backups. Pocket files are **not encrypted**, so protect your data folder and backups. Remote DashDash mode sends only the targets you explicitly submit; local lookups never upload them.

## Develop and contribute

**Stack:** Python 3.10+, Tkinter/ttk, native Windows APIs, Pillow, tkinterdnd2, and PyInstaller.

```powershell
git clone https://github.com/Dovshmi/Pocket.git
cd Pocket
py -3 -m pip install -r requirements.txt
py -3 app.pyw
```

**Tests and Windows packaging:**

```powershell
py -3 -m unittest discover -s tests -p "test_*.py" -v
.\build-portable.bat
.\build-exe.bat
```

GitHub Actions runs Windows/Linux regression checks, GUI smoke tests, and packaged Windows startup/integrity checks for releases. The portable build bundles its own Python runtime and only public example commands.

**Useful links:** [Release history](https://github.com/Dovshmi/Pocket/releases) · [Project layout](docs/REPOSITORY_LAYOUT.md) · [Report an issue](https://github.com/Dovshmi/Pocket/issues)

---

<div align="center">

**Pocket — small tools, one workspace.**

GPL-3.0 · Windows 10/11

</div>
