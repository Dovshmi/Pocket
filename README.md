# PocketDesk

**Your everyday tools, one click away.** PocketDesk is a compact, movable **Windows system-tray utility** for notes, shortcuts, network diagnostics, CLI references, and subnet calculations — without opening six separate apps.

![PocketDesk — Notes view](preview-window-position.png)

**Current version:** `v1.18` · **Platform:** Windows 10/11 · **Built with:** Python 3.10+ / Tkinter · **Data:** Local-first, no account required

## Features

| Tool | What it does |
| --- | --- |
| 📝 **Notes** | Autosaving notes with a title, phone number, creation timestamp and full-width editor. Pin, duplicate or delete notes from the note list. Right-click the editor for standard text actions, date/time insertion, Notepad export, IP lookup or CLI search. |
| 🔗 **Shortcuts** | Save and launch websites, files and folders. Add shortcuts manually or drag a URL/File Explorer item into the app, review the details, then save. |
| 🔌 **TCP Ports** | Test a single TCP port, common presets, or custom port lists/ranges against IPv4/IPv6 targets. View open/closed/timeout/error results and copy or export them. |
| 🖥️ **MAC Lookup** | Identify vendors from MAC addresses using IEEE OUI data. Supports multiple addresses, registry download/import and CSV export. |
| ⌨️ **Commands** | Search network CLI commands and descriptions by device/vendor and category, edit commands before copying, and save custom commands and favorites. Examples cover Cisco, FortiGate, Juniper and Nokia. **Commands are copied, never executed.** |
| 🧮 **Subnet Calculator** | Calculate IPv4 networks from CIDR or subnet masks: network/broadcast, wildcard, address counts, usable host range and smaller subnet splits. Supports `/31` and `/32`. |

### App-wide conveniences

- **System tray:** click the tray icon to show or hide the popup; closing the window hides it rather than erasing data.
- **Global hotkey:** `Ctrl + Shift + *` (including `Ctrl+Shift+8` and numpad `*`, where available).
- **Movable window:** drag the header; PocketDesk remembers its position and keeps it on-screen when possible. Right-click the header to **Reset window position**.
- **PIN mode:** keep the popup visible while working in other windows.
- **Local persistence:** your notes, shortcuts, custom commands and preferences are saved on your PC.

## The app at a glance

Click any screenshot to see it at full size.

<table>
<tr>
<td align="center"><a href="preview-notes-pinned-v117.png"><img src="preview-notes-pinned-v117.png" width="220" alt="Notes tab"></a><br><b>Notes</b></td>
<td align="center"><a href="preview-shortcuts-fixed.png"><img src="preview-shortcuts-fixed.png" width="220" alt="Shortcuts tab"></a><br><b>Shortcuts</b></td>
<td align="center"><a href="preview-ports.png"><img src="preview-ports.png" width="220" alt="TCP Ports tab"></a><br><b>TCP Ports</b></td>
</tr>
<tr>
<td align="center"><a href="preview-mac.png"><img src="preview-mac.png" width="220" alt="MAC Lookup tab"></a><br><b>MAC Lookup</b></td>
<td align="center"><a href="preview-commands-layout.png"><img src="preview-commands-layout.png" width="220" alt="Commands tab"></a><br><b>Commands</b></td>
<td align="center"><a href="preview-subnet-v117.png"><img src="preview-subnet-v117.png" width="220" alt="Subnet tab"></a><br><b>Subnet Calculator</b></td>
</tr>
</table>

## Install & run

1. Install **Python 3.10+** on Windows (with Tkinter).
2. [Download this repository](https://github.com/Dovshmi/Pocket/archive/refs/heads/main.zip) and extract it, or clone it:
   ```powershell
   git clone https://github.com/Dovshmi/Pocket.git
   cd Pocket
   ```
3. Double-click **`run.bat`**. It installs missing Python dependencies and starts the app.
4. Open PocketDesk from the notification area near the Windows clock (check the **^** overflow menu).

**Optional:** use `install.bat` to install dependencies separately, then launch `app.pyw`. Native drag-and-drop uses `tkinterdnd2`; the tray and global hotkey require Windows.

### Build a Windows executable

Run **`build-exe.bat`** on Windows to package the app with PyInstaller. Output: `dist\PocketDesk.exe`.

> **Build safely:** A local `commands/commands.json` file can be bundled into the EXE. Build public distributions from a clean checkout containing **only** the sample commands. This repository does **not** provide a prebuilt EXE; native packaging and multi-monitor behavior still need real-Windows verification.

## Version history

| Version | What's new |
| --- | --- |
| **v1.18** · Oct 27, 2026 | Drag-to-move window, saved/restored position and reset option. |
| **v1.17** · Oct 27, 2026 | IPv4 subnet calculator; pin, duplicate and delete notes. *(Included in the v1.18 GitHub commit.)* |
| **v1.16** · Oct 27, 2026 | Full-width Notes editor, note context menus and shortcut fixes. |
| **v1.10** · Oct 27, 2026 | Consistent taller tab layout and multiline command editor. |
| **v1.6** · Oct 26, 2026 | Windows tray app, notes, shortcuts, CLI reference and network tools. |

See the [commit history](https://github.com/Dovshmi/Pocket/commits/main/) for implementation details. This table tracks significant milestones, not every intermediate iteration.

## Storage, privacy & safety

PocketDesk stores personal data locally under `%APPDATA%\PocketDesk\`:

- `data.json` — notes, shortcuts, preferences, custom commands and window position.
- `vendors.json` — imported/downloaded MAC vendor data.
- `notepad_exports\` — text snapshots opened in Windows Notepad (**changes in Notepad do not sync back**).

**Data is stored in plain text, not encrypted.** Don't save passwords or other secrets without protecting your PC. Port checks and IEEE registry updates access the network only when you request them. **Only scan systems you own or are authorized to test.**

The public repository includes **sample CLI commands only**. Your private command library belongs in `commands/commands.json` on your local PC and is excluded from Git; never commit proprietary or workplace-specific commands.

## Development

Run the unit tests:

```powershell
py -3 -m unittest discover -v
```

The repository also contains GUI smoke-test scripts. Passing those tests does not replace verification of native Windows tray behavior.

## License

See [LICENSE](LICENSE).
