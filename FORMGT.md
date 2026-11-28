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

Mini introduction → four RTL notes with actual Mini paging, an animated added task and autosave (optional real Windows Notepad) → three Hebrew shortcut folders (Work and Studies expanded, More collapsed) → six-device interface command search and paging → Subnet calculation, /30 split and return to top → simulated TCP → four-MAC table, vendor summary and Cisco filter → Clipboard work-session text history and five varied images → Hebrew REBAR follow-up and linked Clalit note reminder → Extra Net customer search → centered Ctrl+K examples and return to Notes → three factory layouts (Mini, Normal, Dashboard), fast browsing through nine tools in each → Dashboard business impact.

The speech bubble appears at desktop center, fades in, then clears before the tool action. Long results are scrolled into view automatically. The left-side controller is independent of Pocket's window layout. Five independent timing channels (Step, Bubble Hold, Fade In, Fade Out and Typing) support 0.10×, 0.25×, 0.50×, 0.75×, 1×, 1.25×, 1.5×, 2× and 3×, with live changes. Step controls result dwell; bubble fade/hold and typing finish before automatic advance. Pocket uses the original borderless window style. Larger Hebrew captions are designed for projection; optional Dim darkens the desktop only while a bubble is visible. Gold input markers and turquoise result outlines with a pointer and label guide attention. Typing is animated for the additional note task, CLI search, subnet, TCP target/ports, four MACs, clipboard search, Extra Net and palette. Manual mode completes the current step but waits for Next. Pause freezes the presentation timeline, not already-started local workers. The final layout tour uses the same Step speed as the rest of the presentation: approximately 0.62 seconds per tool at 1×, with short pauses at each layout change. The existing tools are only opened, not rerun. On a monitor too small for the Dashboard breakpoint, the application retains its actual responsive layout. The final dashboard shows a clearly labeled illustrative capacity scenario, not measured AHT improvement.

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

The four Notes are preloaded in RTL and the automatic chapter pages through all four, types one extra task in the last note, preserves RichEdit paragraph direction and right alignment at every animation frame, and saves it via Pocket's normal autosave. There is no imitation Notepad window and no automatic external-editor chapter. During Notes, the side-controller Windows Notepad button opens the genuine Windows application on the isolated Tasks file. Edit, press Ctrl+S, then close or minimize Notepad; playback waits for the actual synchronization or the presenter can skip with Next. No keystrokes are injected into an external process. Notepad controls its own RTL reading order.

## Local scenario (optional)

Place an approved, private `formgt-scenario.local.json` alongside `app.pyw` or `Pocket-FORMGT.exe`. This file is intentionally gitignored and is not bundled in CI artifacts. Without it the demo runs with generic sample circuit and IP identifiers; the presenter bar explicitly displays SAMPLE DATA rather than LOCAL SCENARIO. The configuration can also be one folder above the executable or supplied explicitly using `Pocket-FORMGT.exe --formgt-scenario "C:\\path\\formgt-scenario.local.json"` (or `py -3 app.pyw --formgt-scenario "C:\\path\\formgt-scenario.local.json"`). The JSON schema is:

```json
{"customer":"Example Business","circuit":"90021400","vrf":"Training","public_ip":"192.0.2.52","port":"10443","vpn_users":"ALEX, JORDAN","phone":"","vdom":"TRAINING","forti_ip":"10.238.2.25","group":"DEMO-G01"}
```

The optional port, vpn_users, phone, vdom, forti_ip and group fields are backward compatible. Five varied original demo images are generated in RAM and displayed by Pocket’s actual image gallery; no host clipboard is read. The selected local scenario feeds Notes, Extra, the linked note reminder, Clipboard and simulated TCP checks. The standalone reminder is a fictional REBAR callback. Shortcut files are temporary demo files without credentials; website opening stays blocked. Never commit customer identifiers, or show them to audiences who are not authorized to view them. No real scan is performed, even for a public IPv4 address.

The MAC example uses four synthetic device addresses with real vendor prefixes: two Cisco, one Alcatel-Lucent Enterprise and one Fortinet (FortiGate). All are local fixture lookups, not actual discovered devices.

## Isolation and limits

The demo creates a fresh temporary synthetic profile, command catalog, Excel workbook and local SQLite index. No existing Pocket profile or private commands are loaded. Clipboard capture, tray hotkeys, external links, Outlook, workbook selection and IEEE downloads are disabled in the walkthrough. TCP outcomes and timings are simulated and labeled. MAC lookup uses a small local fixture. CLI references are not executed. Temporary data is removed on normal exit. This is a presentation mode, not a security sandbox; do not enter real customer details.

## Verification

```powershell
py -3 app.pyw --formgt-smoke
```

The smoke check visits every chapter, checks Mini mode, independent timing clocks, borderless appearance, side controls, Extra results/selection, CLI matching, subnet calculation, simulated TCP, four offline MAC results and vendor grouping, five image records, four-note paging, typed task and save, actual RTL paragraph formatting during and after editing, 27 tool visits across the three layouts, three shortcut folders and their expansion states, REBAR reminder, Extra VDOM/FortiGate/group fields, palette navigation and replay. A separate workflow builds a Windows distribution only after the smoke test passes. Before presenting, manually verify Hebrew layout, native Windows focus and display scaling on the intended machine.
