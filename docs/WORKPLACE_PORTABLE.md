# Pocket Portable on a managed Windows PC

Use the ready-to-run release ZIP from [GitHub Releases](https://github.com/Dovshmi/Pocket/releases/latest).
It already contains the application, Python runtime, Tk/Tcl, Pillow, and native
Windows extensions. **Do not install Python on the target computer.**

1. Download `Pocket-Portable-v1.32.2.zip` from the GitHub Release.
2. Extract the WHOLE ZIP to a *new local writable folder* (e.g. Documents).
3. Run `PocketDesk.exe`. Keep `_internal` alongside it.
4. To upgrade, close Pocket (including tray), back up the `data` folder,
   extract the new release to another folder, and copy your existing `data`
   folder only after the new EXE works.
5. Notes, command helper, clipboard, subnet calculator, settings, and
   other offline features do not need internet. Network checks use network
   connectivity only when invoked.

If it fails, the optional `Verify-Pocket.ps1` checks SHA-256 of all shipped
files and attempts an import/render test for `_ctypes`, `unicodedata`,
`_tkinter`, and `PIL._imaging`. Run scripts only if permitted by your IT
policy. A missing or changed file suggests incomplete extraction, transfer
corruption, or quarantine; re-extract to a fresh folder.

When all hashes match but a DLL or EXE is still blocked, your IT department
should inspect Defender/EDR/AppLocker/WDAC events. Do not disable or bypass
endpoint protections. This release is unsigned and may require approval.

The public release contains **only the application and public example
commands**; it does not package private commands, notes, or saved clipboard.
