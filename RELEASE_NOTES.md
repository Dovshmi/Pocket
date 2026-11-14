# Pocket v1.34.0 — Clipboard Images & Organized Shortcuts

**Stable feature release · Windows 10/11 · Portable ZIP + standalone EXE**

This release brings image-aware clipboard history and practical shortcut organization to every Pocket layout. It includes all improvements previously validated on the `feature/shortcuts-clipboard` branch, while retaining the local-first and opt-in networking behavior from v1.33.1.

## Clipboard — images alongside text

- Separate **Text** and **Images** pages, with a compact switch. Text keeps its search, pin/unpin, copy, and deletion tools.
- Capture Windows screenshots (including `Win+Shift+S`) and bitmaps copied from supported applications such as Word or browsers.
- Images remain **in RAM only** and are never uploaded or written to Pocket data files. The image list holds **at most 20** pictures; when full, the oldest is removed automatically. Text history is independent.
- Copy an older screenshot back to the real Windows clipboard, preview it, or delete it. The original bitmap is used for copying; thumbnails are only for the on-screen gallery.
- **Mini / Extra Mini:** horizontal image gallery, wheel navigation and left/right keyboard arrows, selection highlight and item counter. Normal and Dashboard retain a responsive grid.
- `Enter` previews, `Ctrl+C` copies, and `Delete` removes the selected image. The image selection persists when switching between Text and Images.
- Text context menus provide relevant, safe actions to prefill Ports, MAC Lookup and Subnet Calculator, or create a new Note. No network check starts just from using the context menu.
- Notes right-click menus are grouped by text editing, text direction, note actions, and operations on selected text.

**Limits:** Image capture depends on the source application exposing a supported bitmap clipboard format. Rich Word formatting is not reproduced. Huge image data may be rejected for memory safety. Clipboard monitoring runs only when its tool is visible and capture is enabled.

## Shortcuts — folders, drag and an improved layout

- Create **Pocket organizer folders** that appear as compact, collapsible headings—not as normal shortcut cards and not as real Windows folders.
- Reorder folders and shortcuts using discreet **right-edge `⋮⋮` drag handles**, including dragging shortcuts into or out of folders.
- A single **`+ Add ▾`** menu lets you choose **New shortcut** or **New Pocket folder**.
- Drop a validated external website/file/folder target directly on a Pocket folder to create a shortcut **inside that folder immediately**. Drops on the general area still open the editable review form.
- Save folder positions, shortcut positions and expanded/collapsed state locally. Searching can temporarily reveal matching shortcuts inside a collapsed folder.
- Renaming or deleting an organizer folder never renames or deletes filesystem paths. Deleting an organizer folder returns its contained shortcuts to the main list.
- Existing flat shortcuts and their targets are migrated without losing IDs or changing launch behavior. Mini, Normal and Dashboard use the same saved organization.

## Reliability, security and compatibility

- The previous Windows proxy/PAC/WPAD support for **explicit** DashDash requests remains available. Local checks remain the default.
- Pocket does not execute copied CLI reference commands and does not run TCP/MAC checks without an explicit user action.
- User notes, shortcuts, layout preferences and commands remain local. **Clipboard text and images are session-only** and cleared on exit.
- Official release ZIP and EXE include **only sanitized example commands**, not personal notes, private commands/passwords, or other user data.
- Tests include Windows/Linux unit coverage, GUI tests in all layouts, a real Windows image clipboard copy/read-back test, portable packaging validation, native dependency checks and executable startup.

## Downloads

- **Pocket-Portable-v1.34.0.zip** — full extracted-app package for Windows, including `PocketDesk.exe`, the `_internal/` runtime, integrity manifest and verification script.
- **Pocket-v1.34.0.exe** — standalone Windows executable.
- **SHA256SUMS.txt** — SHA-256 hashes of both release packages.

## Upgrade safely

1. Fully **Exit Pocket**, including from the system tray.
2. Back up your existing user data before replacing anything: `Pocket-Portable/data/` for portable or `%APPDATA%\PocketDesk\` for standalone. Preserve personal `commands.json`.
3. **Portable:** extract the new ZIP into a **fresh writable folder** (never mix old and new `_internal/` files), then move your personal `data/` folder into the new `Pocket-Portable/` folder.
4. Launch `PocketDesk.exe`; verify your notes, commands, existing shortcuts and settings. Your old shortcuts should appear in the unfiled section until you organize them.
5. Test a Windows screenshot with `Win+Shift+S`, then try adding one Pocket folder and moving a shortcut into it.

**Security:** Binaries are unsigned. Respect corporate application-control rules; ask IT before running on a managed work computer. Clipboard history may contain sensitive information; its plaintext remains in RAM only, and the sensitive-text filter applies to recognized sensitive text.
