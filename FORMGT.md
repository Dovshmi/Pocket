# Pocket | FORMGT — Management demonstration

This separate branch is based on Pocket v1.43. Each normal launch opens the real application in its original **Mini mode** (346 × 530), then automatically runs a guided tour with short Hebrew explanation cards inside the Pocket window. No separate controller window or network service is needed.

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

The explanation card appears across the header for about 2.6 seconds, then clears before the tool action. Long results are scrolled into view automatically. The slim controller stays inside Pocket. The final dashboard shows a clearly labeled illustrative capacity scenario, not measured AHT improvement.

| Control | Keyboard |
| --- | --- |
| Replay | F5 |
| Pause / resume | F6 |
| Back | F7 |
| Next | F8 |
| Show explanation again | F9 |
| Exit | Esc |

The real Ctrl+K popup has its own keyboard focus; use its Escape key to dismiss it before using the presenter hotkeys. The automatic run takes about 90 seconds, ending at the summary. Replay returns to Mini.

## Isolation and limits

The demo creates a fresh temporary synthetic profile, command catalog, Excel workbook and local SQLite index. No existing Pocket profile or private commands are loaded. Clipboard capture, tray hotkeys, external links, Outlook, workbook selection and IEEE downloads are disabled in the walkthrough. TCP outcomes and timings are simulated and labeled. MAC lookup uses a small local fixture. CLI references are not executed. Temporary data is removed on normal exit. This is a presentation mode, not a security sandbox; do not enter real customer details.

## Verification

```powershell
py -3 app.pyw --formgt-smoke
```

The smoke check visits every chapter, checks Mini mode, integrated controls, Extra results/selection, CLI matching, subnet calculation, simulated TCP, offline MAC, palette navigation and replay. A separate workflow builds a Windows distribution only after the smoke test passes. Before presenting, manually verify Hebrew layout, native Windows focus and display scaling on the intended machine.
