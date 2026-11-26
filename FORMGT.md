# Pocket | FORMGT (Management demonstration)
 
This branch is deliberately separate from production. Based on v1.43 source, every normal launch opens the real Pocket Dashboard and automatically starts a guided, roughly 90-second presentation. No external service is required for playback.
 
## Start
 
```powershell
git clone -b FORMGT https://github.com/Dovshmi/Pocket.git Pocket-FORMGT
cd Pocket-FORMGT
py -3 -m pip install -r requirements.txt
.\RUN-FORMGT.bat
```
 
To build a separate Windows distribution, run `BUILD-FORMGT.bat` on a Windows development machine with Python 3.11 x64. Open `dist\FORMGT\Pocket-FORMGT\Pocket-FORMGT.exe` and keep the entire folder (including _internal). This is a local build recipe, not a published release. Use only on approved workstations; the binary is unsigned.
 
## Presentation
 
Dashboard → Ctrl+K → Extra (real SQLite lookup of synthetic records) → Commands → Subnet → simulated TCP → offline MAC → restore Extra → Notes → Clipboard → Reminders → Shortcuts → business impact.
 
Use Previous, Next, Pause / Resume, Replay or Exit in the floating presenter panel. On smaller screens, drag the panel away from the application. Timings are playback intervals, **not measured productivity gains**. The final slide is an illustrative calculation, not a pilot result.
 
## Data isolation
 
A disposable synthetic profile, command catalog, Excel workbook and SQLite index are generated at launch. No existing Pocket profile or private command catalog is loaded. Clipboard polling, tray hotkeys, external links, Outlook, workbook selection and vendor downloading are disabled for the walkthrough. TCP statuses are simulated, not evidence of real connectivity. MAC resolution uses a tiny local fixture. No production CLI is executed. The temporary directory is removed on normal exit; an interrupted process may leave synthetic files.
 
This is a presentation mode, not a security sandbox or production release. Do not enter real customer details. Use the main branch for normal work.
 
## Test
 
```powershell
py -3 app.pyw --formgt-smoke
```
 
The smoke flag visits all steps and verifies the real Extra search, CLI matches, subnet math, simulated TCP results and MAC output. GitHub Actions workflow is scoped to FORMGT. Test on the intended Windows display before the meeting.
