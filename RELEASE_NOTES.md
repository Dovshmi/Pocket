# Pocket v1.32.1 — Windows Pillow Packaging Fix

**Maintenance release · Windows 10/11 · Local-first · Unsigned EXEs**

This update addresses the portable-build startup error `ImportError: cannot import name '_imaging' from 'PIL'` observed on another Windows computer. It does not change Pocket's features, notes format, saved settings, or network behavior.

## Fixes and verification

- Collect the entire Pillow (`PIL`) package, including compiled `_imaging` / `_imagingtk` binaries, in both Windows PyInstaller builds.
- Include an isolated `--self-test-deps` check that actually imports Pillow's compiled imaging extension, creates a test image, initializes Tkinter, and renders an ImageTk image. It requires no internet or Python installation on the destination computer.
- During GitHub Actions release publishing, extract the *finished portable ZIP* into a fresh directory, confirm that Pillow's compiled extension is present, run the packaged dependency self-test, and launch both the extracted portable EXE and standalone EXE. A failed check blocks publication.
- Preserve the existing UI, clipboard privacy, manual-only command backups, and offline-first behavior.

## Downloads

- **Pocket-Portable-v1.32.1.zip** — recommended for work: extract the complete ZIP to a new local writable folder, then run `PocketDesk.exe`.
- **Pocket-v1.32.1.exe** — standalone executable, stores user data in Pocket's normal AppData location.
- **SHA256SUMS.txt** — download checksums.

## Upgrade safely

1. Exit the old Pocket application fully, including the tray icon.
2. Back up your `data/` directory and any personal command-library file.
3. Extract v1.32.1 into a **new** folder. Do not mix old and new `_internal/` files.
4. Copy your backed-up portable `data/` folder into the new portable directory only after first checking that the fresh release launches.

**Corporate Windows note:** The build is unsigned, and corporate antivirus/application-control policies may prevent DLL loading even if all files are included. These tests verify the binaries on GitHub's Windows runner, not the policy or hardware of every workplace machine. If the issue persists after a clean extraction, ask IT to check whether `PIL/_imaging*.pyd` was blocked or quarantined. Do not disable corporate protections.

No private notes, private command libraries, backups, or other personal data are included in release artifacts.
