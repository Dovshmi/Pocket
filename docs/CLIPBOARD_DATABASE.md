# Pocket v1.38 — Clipboard history: RAM or local DATABASE

Pocket stores clipboard content **offline**. The Clipboard menu now has a compact **Storage** dropdown (RAM / DATABASE) beside a date selector in Mini, Normal and Dashboard layouts.

- **RAM (default):** the original session-only text and screenshot history. Nothing is written to disk. The number of screenshots **stored** in RAM can be set to 10, 15, 20, 25 or 30 (default 20). Closing Pocket clears RAM history.
- **DATABASE (opt-in):** text history and screenshots survive a restart in the Pocket data folder. The settings specify how many items **to show per batch** (screenshots: 10–100 in tens; text: 100, 300, 500, 800, 1000, 1200, 1500), not how many are retained on disk. Scroll toward the end of the Text list or Images gallery to load more history automatically. There is no extra Prev/Next row. Full-resolution screenshots are read on demand for copy/preview; history navigation stores only a bounded set of metadata/thumbnail objects in RAM.

Switching modes does **not** import old RAM entries into DATABASE or expose DATABASE entries while in RAM mode. The chosen storage mode is stored in Pocket preferences; no clipboard content is written into `data.json`.

## Local file layout

Portable Pocket saves beneath `Pocket-Portable/data/ClipboardDatabase/`.
Standalone Pocket saves beneath `%APPDATA%/PocketDesk/ClipboardDatabase/`.

```text
ClipboardDatabase/
├── ClipboardText/
│   ├── 2026-11-17_08-30-00_to_saved.txt
│   └── 2026-11-18_09-15-12_to_saved.txt
└── ClipboardScreenshots/
    ├── 2026-11-17_01-53-27_4f1c...png
    ├── 2026-11-17_02-14-08_7e92...png
    └── 2026-11-18_09-30-12_ab40...png
```

**Text:** Pocket keeps one UTF-8 `.txt` file per calendar day. Each entry is one JSON line with its text, timestamp, id and pin status. Every new copy **appends a line**, avoiding the cost of rewriting the entire day for each copy. Pin/unpin or deletion may atomically rewrite that day's file, preserving hidden entries. Older v1.37 files using newest-first lines are converted on their next write without discarding their contents. `to_saved` means automatic deletion is **OFF**.

**Screenshots:** a **single flat folder** holds all accepted PNGs; the first part of each filename is `YYYY-MM-DD` so that day filtering is quick. Images are stored as separate files and are not constrained by the 10–100 display count. The full UUID suffix avoids filename collisions.

On first opening DATABASE in v1.37, Pocket migrates the previous `ClipboardScreenshots/YYYY-MM-DD/HH-MM-SS_<id>.png` layout to the flat naming scheme. This move is idempotent: files with conflicting names are **never overwritten**, and unexpected files are left untouched in their original folders. Back up the Pocket `data` folder before upgrading.

## Display and navigation

- Each page (Text and Images) has a **History date** dropdown, shown only when DATABASE is selected.
- Each page keeps its own chosen date while Pocket is running. Selecting a date starts with 10–100 entries; scrolling automatically extends the visible history in batches without loading the full archive at once.
- Copying text or a screenshot (even if identical to the most recent item) returns that respective page to **Today** without clearing older dates.
- **Clear day** deletes Pocket-managed items **only for the selected day and type**; deleting a single item affects only that entry.
- RAM limits and DATABASE display limits are **separate**. Default DATABASE text batch limit: 100; screenshot batch limit: 30. Four compact Settings dropdowns are arranged in a 2×2 grid; wheel-scrolling over these choices scrolls Settings without changing their selection. Other dropdowns are unaffected. You may select 10, 20, ..., 100 screenshots or 100/300/500/800/1000/1200/1500 text entries per batch and scroll to access older items. The grey Text status line shows the selected item index and number of displayed entries, mirroring the Images status without adding another row.
- Text remains searchable within the currently displayed page. Other pages/dates are accessible through navigation.

## Automatic cleanup: OFF / 7–30 days

The **Automatic history cleanup** dropdown is under **Settings → Clipboard & privacy**. Available choices: **Off** (factory default), and every whole-day period from **7 through 30 days** (inclusive). The setting applies to **both daily text files and screenshot PNGs**.

- **Off:** files remain on disk until you explicitly clear/delete them. Historical settings that previously limited history to 1–5 days are *not* silently interpreted as permission to delete files.
- **7 days:** today and the preceding 6 calendar dates are retained.
- **30 days:** today and the preceding 29 dates are retained.
- Changing from OFF to a retention duration immediately removes expired Pocket-managed files. Cleanup also runs on startup, at midnight while Pocket is open, and after changing the retention setting.
- Daily text filenames are re-labeled with their planned expiration date (e.g. `_to_2026-11-24.txt`) when auto-delete is enabled. When disabled again, remaining files are re-labeled `_to_saved.txt`.

Deletion is an ordinary file delete, not cryptographic erasure. Backups and Windows file recovery could still retain old content.

## Translate controls

The **Enable Translate shortcut**, editable hotkey (factory default **Ctrl+Alt+V**) and **Mark / Clipboard** selection are grouped in the same Clipboard & privacy settings section. Mark (default for new profiles) changes the physical EN/HE keyboard layout of selected text and replaces it in the active Windows app; it does **not** translate the language's meaning or call an online service.

## Privacy and workplace use

**DATABASE is plain, unencrypted local storage.** The heuristic sensitive-text filter cannot guarantee that passwords, internal data or customer details are excluded, and it cannot screen sensitive information inside screenshots. Enable persistent history on a work computer only if corporate policy permits it. Consider the access permissions and encryption status of the Windows device. No history is automatically sent to DashDash, the network, or external servers. Pocket's release ZIP excludes `ClipboardDatabase` and the entire personal `data` directory.
