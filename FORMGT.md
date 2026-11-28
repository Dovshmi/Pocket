# Pocket | FORMGT — Management demonstration

This separate branch is based on Pocket v1.43. Each normal launch opens the real application in its original **Mini mode** (346 × 530), then automatically runs a guided tour with rounded Hebrew speech bubbles centered on the desktop, with a separate left-side presenter bar. No network service is needed.

## Run

```powershell
git clone -b FORMGT https://github.com/Dovshmi/Pocket.git Pocket-FORMGT
cd Pocket-FORMGT
py -3 -m pip install -r requirements.txt
.\RUN-FORMGT.bat
```

Build on a Windows development PC with Python 3.11 x64 using `BUILD-FORMGT.bat`. Run `dist\FORMGT\Pocket-FORMGT\Pocket-FORMGT.exe` from the complete output folder. The binary is unsigned; use only on approved workstations. The FORMGT GitHub Actions workflow also attempts a Windows artifact build after the GUI smoke test passes.

## Presentation

Mini introduction → four RTL notes with actual Mini paging → external text editor save/sync → organized Shortcuts → CLI search and favorite → Subnet calculation and /30 split → simulated TCP → four-MAC table, vendor summary and Cisco filter → Clipboard text and image carousel → linked reminder → Extra Net → Ctrl+K back to Notes → Dashboard business impact.

The speech bubble appears at desktop center, fades in, then clears before the tool action. Long results are scrolled into view automatically. The left-side controller is independent of Pocket's window layout. Five independent timing channels (Step, Bubble Hold, Fade In, Fade Out and Typing) support 0.10×, 0.25×, 0.50×, 0.75×, 1×, 1.25×, 1.5×, 2× and 3×, with live changes. Step controls result dwell; bubble fade/hold and typing finish before automatic advance. Pocket uses the original borderless window style. Larger Hebrew captions are designed for projection; optional Dim darkens the desktop only while a bubble is visible. Gold input markers and turquoise result outlines with a pointer and label guide attention. Typing is animated for the external note editor, CLI search, subnet, TCP target/ports, four MACs, clipboard search, Extra Net and palette. Manual mode completes the current step but waits for Next. Pause freezes the presentation timeline, not already-started local workers. The final dashboard shows a clearly labeled illustrative capacity scenario, not measured AHT improvement.

| Control | Keyboard |
| --- | --- |
| Replay | F5 |
| Pause / resume | F6 |
| Back | F7 |
| Next | F8 |
| Show explanation again | F9 |
| Toggle Auto / Manual | F10 |
| Select timing channel | F11 |
| Reset all rates | F12 |
| Faster (selected channel) | Ctrl+Up |
| Slower (selected channel) | Ctrl+Down |
| Exit | Esc or side button |

Presenter shortcuts work while a FORMGT process window has focus; the real Ctrl+K popup uses Escape to dismiss itself. The automatic run takes roughly two minutes at default timing, ending at the summary. Replay returns to Mini.

## Notes / Notepad

The four Notes are preloaded and all use RTL. The automatic chapter advances through all four with the real Mini note navigation, then opens a clearly labeled automatic demo editor for the last note. It writes a real UTF-8 working file, calls Pocket's normal Notepad synchronization and shows the saved change in Pocket. This editor is not the Windows Notepad application. During the Notepad chapter, select **Windows Notepad** in the side controller to open the actual application instead; edit the isolated note, press Ctrl+S and close or minimize Notepad. Playback waits until the saved edit is imported (or use Next to skip). The normal Pocket Notepad button also opens the actual working file. The demo does not automate keystrokes into external processes. For the actual Notepad app, right-to-left reading order is controlled by Notepad itself.

## Local scenario (optional)

Place an approved, private `formgt-scenario.local.json` alongside `app.pyw` or `Pocket-FORMGT.exe`. This file is intentionally gitignored and is not bundled in CI artifacts. Without it the demo runs entirely with generic sample circuit and IP identifiers. The JSON schema is:

```json
{"customer":"Example Business","circuit":"90021400","vrf":"Training","public_ip":"192.0.2.52","port":"10443","vpn_users":"ALEX, JORDAN","phone":"","vdom":"training","forti_ip":"10.238.2.25"}
```

The optional port, vpn_users, phone, vdom and forti_ip fields are backward compatible. Three original mock screenshots are generated in RAM and displayed by Pocket’s actual image gallery; no host clipboard is read. Only the selected local scenario feeds Notes, Extra, Reminders, Clipboard and simulated TCP checks. Never commit customer identifiers, or show them to audiences who are not authorized to view them. No real scan is performed, even for a public IPv4 address.

The MAC example uses four synthetic device addresses with real vendor prefixes: two Cisco, one Alcatel-Lucent Enterprise and one Fortinet (FortiGate). All are local fixture lookups, not actual discovered devices.

## Isolation and limits

The demo creates a fresh temporary synthetic profile, command catalog, Excel workbook and local SQLite index. No existing Pocket profile or private commands are loaded. Clipboard capture, tray hotkeys, external links, Outlook, workbook selection and IEEE downloads are disabled in the walkthrough. TCP outcomes and timings are simulated and labeled. MAC lookup uses a small local fixture. CLI references are not executed. Temporary data is removed on normal exit. This is a presentation mode, not a security sandbox; do not enter real customer details.

## Verification

```powershell
py -3 app.pyw --formgt-smoke
```

The smoke check visits every chapter, checks Mini mode, independent timing clocks, borderless appearance, side controls, Extra results/selection, CLI matching, subnet calculation, simulated TCP, four offline MAC results and vendor grouping, three image records, four-note paging, RTL, persisted working-file edits, Extra VDOM/FortiGate fields, palette navigation and replay. A separate workflow builds a Windows distribution only after the smoke test passes. Before presenting, manually verify Hebrew layout, native Windows focus and display scaling on the intended machine.
