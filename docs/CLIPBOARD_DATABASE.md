# Pocket v1.37 — Clipboard RAM / Local Database

Pocket's Clipboard menu has two explicitly selectable storage modes, available on the Text and Images pages:

- **RAM (factory default):** the original session-only text and screenshot history. It is discarded when Pocket exits. Screenshot history is capped at the selected 10–30 images (20 default).
- **DATABASE (opt-in):** save accepted clipboard text and PNG screenshots **locally**, separated by day. History survives a restart. Screenshot history is not limited by the RAM screenshot count.

Both modes are offline. Switching modes does not upload anything, copy old RAM entries into DATABASE, or migrate stored entries back into RAM. The chosen storage mode is saved in Pocket preferences.

## Where files are stored

Portable Pocket: `Pocket-Portable/data/ClipboardDatabase/`.
Standalone Pocket: `%APPDATA%/PocketDesk/ClipboardDatabase/`.

Example with two calendar days of history and a one-day retention setting:

```text
ClipboardDatabase/
├── ClipboardText/
│   └── 2026-11-17_22-45-12_to_2026-11-18.txt
└── ClipboardScreenshots/
    └── 2026-11-17/
        ├── 22-45-12_89a34f....png
        └── 22-48-31_43c2a8....png
```

The TXT filename contains the **date and time the daily file was first created** and the **expiry date**, recalculated when the retention setting changes. The file contains each text entry as a UTF-8 JSON record on one line, preserving Hebrew, line breaks, timestamps, pinning, and unique IDs. It is a normal readable `.txt` file, **not a SQLite file**. There is only one managed TXT file per date. Pocket writes changes atomically and does not save clipboard entries inside `data.json`.

Screenshots are saved as metadata-stripped PNG files in a folder named for each capture date. Deleting an item removes its corresponding PNG; clearing a day affects **only the selected date**, not every saved date.

## How the date picker works

The DATABASE mode shows a **History date** selector for the current Text or Images page. Each page remembers its own selected date. Choose a past date to view, search, pin/unpin, copy, preview, or delete entries from that day.

A **new copy** (including an identical repeated copy) returns the corresponding page to **Today**, without discarding other dates. Text captures return the Text view to Today; image captures return the Images view to Today. Switching to RAM hides the date selector.

## Retention: 1–5 calendar days

Under **Settings → Clipboard & privacy → Database history retention**, select **1, 2, 3, 4, or 5 days** (default **1 day**). These are calendar days in the computer's local time: with 1 day, only today is retained, and yesterday expires when the next calendar day starts. With 5 days, today and the preceding four dates remain. Expired Pocket-managed files and screenshots are removed during daily maintenance, startup of DATABASE mode, or changes to retention. Unrecognized files are left untouched. Shortening retention can permanently delete old history.

## Translate shortcut (in the same Clipboard settings card)

- **Enable Translate shortcut:** ON by default, but you may disable its global Windows hotkey entirely.
- **Shortcut:** Ctrl+Alt+V by default; editable without changing the popup hotkey.
- **Mode:** **Mark** by default for a new profile; Clipboard remains available if you prefer the original copy/convert behavior. An already-saved mode preference is respected.

Mark corrects **keyboard positions** between English and Hebrew and replaces selected text in the active Windows application. It is not semantic translation and does not contact any translation service.

## Privacy and workplace use

**DATABASE stores clipboard content in plaintext on disk.** It is not encrypted or password-protected by Pocket. The optional sensitive-text filter skips some recognized credentials/tokens, but it **cannot guarantee** that confidential text or screenshot contents will be excluded. Screenshots may include private information not detected by the text filter.

Only enable DATABASE if your workplace's security/data-retention policy allows retaining copied material. Use Windows storage encryption and file permissions as appropriate; ordinary deletion does not guarantee secure erasure from backups, SSD snapshots or forensic recovery. Pocket never exports this local history to DashDash or another network service. The release ZIP excludes the history directory.

The app stores the data below its **writable profile data directory** (beside the executable for portable installations, under AppData for standalone installations). It does not write into the program's read-only executable or bundled dependency directories.
