# Pocket v1.35.0 — Modern Settings & Everyday Workflow Improvements

**Stable Windows release · Windows 10/11 · Portable ZIP + standalone EXE**

This release collects the features and reliability fixes merged into `main` since v1.34.0. It retains the local-first workflow, the optional Windows proxy/PAC-aware DashDash checks, and the RAM-only clipboard history introduced in v1.34.0.

## Modern Settings and navigation

- Redesigned **Settings** across Normal, Mini and Dashboard with consistent cards, visible mode selections, six direct color choices, accessible switch-style controls and a subtle author/version footer.
- **Mini** is the default layout for **new profiles only**. Existing installations retain their last chosen mode, window placement, theme, shortcuts and notes.
- Pocket now remembers the **last selected tool** and restores it on restart when the tool is still enabled.
- The tiny Extra Mini **`_`** button is available only when Extra Mini is enabled in Settings; header/branding positioning has been polished in Normal and Mini, and `By. Rony Shmidov` appears unobtrusively beneath Pocket.
- Normal **Commands Helper** shows at least four complete result rows while retaining the separate temporary edit-before-copy area.

## Clipboard history and keyboard layout

- Configure clipboard image capacity under **Settings → Clipboard & privacy**: **10, 15, 20, 25, 30**, with **20 as the default** and **30 maximum**.
- Screenshots and clipboard text are **session-only and RAM-only**; the count preference is persisted, not the image bytes. Lowering the limit drops the oldest in-memory images.
- New offline **EN/HE keyboard-layout correction** for accidentally typed characters on the wrong physical-key layout, available from **Clipboard Text → Use text in Pocket → TRANSLATE EN/HE** and via a configurable shortcut (default **Ctrl+Alt+F9**). This is a keyboard-position conversion, **not** semantic translation and requires no network.
- Unavailable context-menu actions stay visible with a **strikethrough** and normal readable text color. They remain disabled and cannot execute.

## Notes editor reliability

- Improved native Windows RichEdit focus handoff so clicking **Title** or **Phone** after editing a note gives those fields keyboard focus, including after dismissing a right-click menu.
- Removed the intrusive white Notes editor scrollbar. Long notes remain scrollable with the mouse wheel, caret and keyboard navigation.

## Useful new-install defaults

The following are **factory defaults only**; upgrades **do not overwrite saved user settings or shortcuts**.

- Mini mode on first launch.
- Quick Shortcuts folder **Ushpelo** with **DashDash** (`https://dashdash-tau.vercel.app`) first and **My GitHub** (`https://github.com/Dovshmi`) second.
- TCP checker prefilled with target `8.8.8.8` and ports `21,22,443,80,8080,3389,53` in **Local** mode. Prefilling never starts a network scan.

## Security, testing and compatibility

- Local tools remain offline by default. TCP checks and remote MAC/vendor lookups run only on explicit request, and remote DashDash traffic continues to use Windows-configured proxy/PAC when needed.
- Pocket never executes saved CLI reference commands.
- Public release archives exclude personal notes, private credentials, user `commands.json`, cached clipboard contents and local data folders. The bundled command library is sanitized example data.
- Release verification includes Windows/Linux unit and GUI tests, native DLL checks, extracted portable integrity checks, and startup of the packaged Portable and Standalone executables.

## Official downloads

- **Pocket-Portable-v1.35.0.zip** — self-contained extracted-app Windows package, including `PocketDesk.exe`, `_internal/`, a SHA-256 bundle manifest and the verification script.
- **Pocket-v1.35.0.exe** — standalone Windows executable.
- **SHA256SUMS.txt** — checksums for both release packages.

## Upgrade without losing your work

1. Fully **Exit Pocket** from the Windows tray.
2. Back up your current profile. Portable: `Pocket-Portable/data/`. Standalone: `%APPDATA%\\PocketDesk/`. Keep your personal `commands.json`.
3. For the portable version, **extract to a NEW writable directory**, rather than merging old and new `_internal/` files. Copy the existing `data/` folder to the new extracted `Pocket-Portable/` folder.
4. Start Pocket and check your saved notes, shortcuts/folders, selected mode and Tools settings.
5. Existing installations keep their current links and ports; **Ushpelo** and the new TCP presets apply only to fresh profiles.

**Security:** Release executables are unsigned. Respect work-PC application control and ask IT where required. Clipboard images and text exist only in RAM while Pocket is running.
