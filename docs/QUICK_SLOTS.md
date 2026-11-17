# Pocket v1.39 — Quick Slots (Numpad 1–9)

A compact, local-first extension of Clipboard **Text** history. No new
Clipboard panel, row, button, or resized control is required.

## Use

By default the Quick Slots prefix is **Ctrl+Alt**. The number keys are always
the **right-hand Numpad**, with **Num Lock ON**:

| Action | Default shortcut |
| --- | --- |
| Arm Save Mode (5 seconds) | `Ctrl+Alt+Numpad0` |
| Paste saved slot 1–9 | `Ctrl+Alt+Numpad1` through `Numpad9` |
| Save to slot 1–9 | Press `Ctrl+Alt+Numpad0`, then `Ctrl+Alt+Numpad1–9` within 5 seconds |

After the next numbered shortcut, Pocket leaves Save Mode automatically,
whether or not the save succeeds. It also leaves Save Mode after five seconds
without a numbered shortcut, or whenever Quick Slots are disabled. A brief
Windows tray notification confirms entry into Save Mode; the main Pocket
window does not need to be opened.

Only one global chord is registered for both actions. **Shift is not used**,
because Shift combined with some numeric keypad buttons produces navigation
key virtual codes on Windows.

## Settings

Open **Settings → Clipboard & privacy**:

* **Enable Quick Slots** — turn the entire feature ON/OFF. When OFF, all
  Quick Slots keyboard shortcuts are unregistered and both the numbered
  rows and assignment actions are hidden from the Clipboard menu. Stored
  assignments are preserved for re-enabling; they are never silently deleted.
* **Quick Slots key prefix** — change only the modifier keys used before
  `Numpad0–9`: `Ctrl+Alt` (default), `Ctrl`, `Ctrl+Win` or
  `Ctrl+Alt+Win`. The Numpad keys are fixed and cannot be changed.
  Windows may reserve some Win-key combinations. If any of the ten new
  combinations cannot be registered, Pocket rejects the change and keeps
  the previous working prefix. Switching preferences does not require a
  restart.
* The prefix selector's mouse wheel scrolls Settings instead of accidentally
  changing the value.

### Saving

1. Select text in the foreground application and press the **Save Mode**
   shortcut (`Ctrl+Alt+Numpad0` by default).
2. Press the chosen numbered shortcut (`Ctrl+Alt+NumpadN`) within five seconds.
3. Pocket borrows the Windows clipboard briefly to copy the selection,
   then restores its original data (including non-text formats).
4. If no fresh nonempty selected text was copied, Pocket uses
   **the text that was in the clipboard before the shortcut**.
5. The slot is persisted locally. No upload or DashDash call occurs.
6. When the destination slot contains different text, Pocket asks for
   confirmation before replacing it. Declining leaves it unchanged.

To avoid accidental storage of secrets, recognizable sensitive text is
rejected while Pocket's Sensitive Text Filter is enabled.

### Pasting

Without arming Save Mode, press `Ctrl+Alt+NumpadN` while focused in a
target application. Pocket temporarily places the chosen text into the
Windows clipboard, issues `Ctrl+V` to the original foreground window,
and attempts to restore the previous multi-format clipboard contents.

Some elevated, remote, or protected applications may refuse injected
paste input; use Pocket's existing **Copy** action followed by manual
`Ctrl+V` if needed.

## Clipboard menu and ordering

Right-click any text row and choose **Assign to Quick Slot**, then
`[1]`–`[9]`. The menu and global shortcut use the **same replacement
confirmation**.

* Assigned slots are shown at the top of the **existing** Listbox as
  `[1] text`, `[2] text`, etc. in numeric order, replacing the star
  in the text prefix. No slot names are stored.
* **Ordinary starred Pins** appear below the numbered slots.
* **Unpinned history** appears last, in its existing newest-first order.
* A slot's text is hidden from ordinary history rows while assigned,
  avoiding duplicate visible Favorites.
* On promotion or replacement, matching historical rows lose their Pin;
  the old value never remains a favorite merely because it used to
  occupy a numbered slot.
* Use the row's right-click **Remove [N] assignment** / **Clear Quick Slot**
  action to clear one number. The underlying unpinned history, when present,
  remains unchanged.
* **Clear text history** removes daily/RAM history but does not silently
  erase deliberate Quick Slot assignments.

## Storage and privacy

Quick Slots are nine explicit strings in the local Pocket profile
`data.json`, independent of RAM clipboard history and optional daily
DATABASE history. They therefore survive a restart, day rollover,
history retention, and RAM-to-DATABASE switching. **Quick Slots persist
even when Clipboard is set to RAM-only**; unlike transient history, the
user must explicitly assign or clear each slot.

Do not store passwords, authentication tokens, private account details, or
other sensitive secrets in a Quick Slot. The profile is not encrypted.

## Implementation and checks

* `pocket/quick_slots.py`: pure sorting/storage/hotkey mapping plus
  one-shot selection capture and paste with OLE clipboard preservation.
* `pocket/clipboard_gallery.py`: compact `[N]` badge in Listbox content,
  and a nine-item right-click submenu.
* `app.pyw`: local profile migration, replacement dialogs, background
  operations and tray hotkey registration. All Tk interactions remain
  on the Tk event thread.
* `tests/test_quick_slots.py`: headless model, clipboard, persistence,
  and replacement regressions.
* `tests/integration/smoke_dashboard_integration.py`: verifies the
  nine entries and unchanged text panel geometry.

This is work-in-progress on `feature/v1.39`; it is not a v1.39 release.
