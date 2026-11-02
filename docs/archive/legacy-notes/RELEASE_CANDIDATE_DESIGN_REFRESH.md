# Pocket design refresh — release candidate checklist

**Status:** Draft; no release has been published. Neither `main` nor the previous Dashboard branch has been modified.

**Branch:** `feature/pocket-design-system-and-polish`  
**Base:** `feature/dashboard-ui-refresh`  
**Next version target:** `v1.29` (not tagged or shipped).

## Implemented
- Theme-derived visual language with consistent tool actions, cards, inputs, table headings and section headers. All original tool callbacks remain in place.
- Offline Quick Search using Ctrl+K; Ctrl+F preserves local Commands search and opens global search elsewhere. Extra Mini keeps its inline search.
- Optional Clipboard Pause/Resume and conservative credential-pattern exclusion; clipboard history stays in RAM. **Pattern filtering does not guarantee that every secret is recognized.**
- Keyboard-focusable actions and a closable, keyboard-navigable search dialog.
- Automated unit, GUI and Windows portable-build/startup checks; isolated UI screenshots available through CI artifacts.

## Automated verification
- [x] Full unit suite on Windows and Linux, Python 3.11/3.13.
- [x] Real Tk GUI smoke on Windows and Linux, all tool pages and all working layouts.
- [x] Extra Mini editing/restore, saved settings and clipboard privacy tests.
- [x] Safe, bounded local Quick Search and privacy regression tests.
- [x] Windows PyInstaller portable ZIP validation, private-data exclusions and isolated startup.

## Required manual Windows QA before merge/release
- [ ] Native Win32 RTL/LTR notes editor focus, context menus, and text saving.
- [ ] System-tray hide/show, global hotkey registration, duplicate launches.
- [ ] Real 100%, 125% and 150% display scaling and multi-monitor placement.
- [ ] Interactive Windows + picker behavior (CI fully clicks the Linux/Xvfb picker).
- [ ] Offline usage, clipboard ordinary text and sensitivity-filter limitations.
- [ ] Portable ZIP move/copy persistence and non-admin work-PC restrictions.
- [ ] Visual review of CI screenshots and final accessible-focus contrast.

Keep the published v1.28 workflow intact until a separate v1.29 release is explicitly approved; this branch does not tag or publish a release.
