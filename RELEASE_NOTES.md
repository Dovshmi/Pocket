# Pocket v1.29.1 — UI Reliability Update

**Windows 10/11 · Free, open source · No Python required to run**

This maintenance release ships the interface fixes already merged into the Pocket `main` branch since v1.29. All existing tools, saved data formats, manual CLI backup behavior, and working layouts are retained.

## Fixed and improved
- **Readable dropdowns:** dark, high-contrast text and option lists for Notes, Commands, Settings and other themed selectors, including selected, focused and disabled states.
- **Dashboard Home scrolling:** mouse-wheel support plus a visible vertical scrollbar to reach all enabled tool cards on shorter displays.
- **Clearer Dashboard navigation:** distinguish informational counters from clickable tool cards; all seven enabled tools have direct Home access.
- **Normal navigation:** more discoverable additional-menu count and Quick Search access.
- **Mini and Extra Mini:** clearer tooltips and improved keyboard navigation without changing their window dimensions.
- **Preserves v1.29 features:** modern Settings, local Quick Search, note reminders, CLI reference manager (copy-only), subnet calculator, TCP/MAC tools, shortcuts, and session-only clipboard history.

## Downloads
- **Pocket-Portable-v1.29.1.zip** — recommended: extract the entire ZIP and run `PocketDesk.exe`. Keep your personal `data/` folder when upgrading.
- **Pocket-v1.29.1.exe** — standalone one-file Windows executable, storing settings in the regular app-data location.
- **SHA256SUMS.txt** — SHA-256 checksums for both public assets.

## Updating from v1.29
Close Pocket completely from the tray first. Make a copy of your current data before updating. In portable mode, preserve the existing `data/` folder when copying new program files; do not overwrite it with an empty folder. The public release bundles only public example commands, never private user notes, credentials or custom command backups.

## Verification and important limitations
Windows and Linux unit/GUI integration tests, a Windows portable ZIP build and an isolated standalone EXE startup check run before publication. The files are unsigned; Windows SmartScreen or workplace policies may restrict execution. Clipboard sensitive-text filtering is heuristic, not a guarantee. Real high-DPI monitors, Windows tray/hotkey behavior and right-to-left notes should still be tested on the end-user machine.

**Smart Command Templates are not included in v1.29.1.**
