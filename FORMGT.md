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

Mini introduction → Notes → Shortcuts → Commands → Subnet → simulated Ports → MAC → Clipboard → Reminders → Extra → switch tools → restore Extra → Ctrl+K → Dashboard business impact.

The speech bubble appears at desktop center, fades in, then clears before the tool action. Long results are scrolled into view automatically. The left-side controller is independent of Pocket's window layout. Speed (0.5×–3×) rescales the active timeline, including bubble dwell, typing and auto-advance. Manual mode completes the current step but waits for Next. Pause freezes the presentation timeline, not already-started local workers. The final dashboard shows a clearly labeled illustrative capacity scenario, not measured AHT improvement.

| Control | Keyboard |
| --- | --- |
| Replay | F5 |
| Pause / resume | F6 |
| Back | F7 |
| Next | F8 |
| Show explanation again | F9 |
| Toggle Auto / Manual | F10 |
| Faster | Ctrl+Up |
| Slower | Ctrl+Down |
| Exit | Esc or side button |

Presenter shortcuts work while a FORMGT process window has focus; the real Ctrl+K popup uses Escape to dismiss itself. The automatic run takes about 90 seconds, ending at the summary. Replay returns to Mini.

## Local scenario (optional)

Place an approved, private `formgt-scenario.local.json` alongside `app.pyw` or `Pocket-FORMGT.exe`. This file is intentionally gitignored and is not bundled in CI artifacts. Without it the demo runs entirely with generic public sample identifiers. The JSON schema is:

```json
{"customer":"Example Business","circuit":"90021400","vrf":"Training","public_ip":"192.0.2.52"}
```

Only the selected local scenario feeds Notes, Extra, Reminders, Clipboard and simulated TCP checks. Never commit customer identifiers, or show them to audiences who are not authorized to view them. No real scan is performed, even for a public IPv4 address.

The MAC example uses four synthetic device addresses with real vendor prefixes: two Cisco, one Alcatel-Lucent Enterprise and one Fortinet (FortiGate). All are local fixture lookups, not actual discovered devices.

## Isolation and limits

The demo creates a fresh temporary synthetic profile, command catalog, Excel workbook and local SQLite index. No existing Pocket profile or private commands are loaded. Clipboard capture, tray hotkeys, external links, Outlook, workbook selection and IEEE downloads are disabled in the walkthrough. TCP outcomes and timings are simulated and labeled. MAC lookup uses a small local fixture. CLI references are not executed. Temporary data is removed on normal exit. This is a presentation mode, not a security sandbox; do not enter real customer details.

## Verification

```powershell
py -3 app.pyw --formgt-smoke
```

The smoke check visits every chapter, checks Mini mode, integrated controls, Extra results/selection, CLI matching, subnet calculation, simulated TCP, offline MAC, palette navigation and replay. A separate workflow builds a Windows distribution only after the smoke test passes. Before presenting, manually verify Hebrew layout, native Windows focus and display scaling on the intended machine.
