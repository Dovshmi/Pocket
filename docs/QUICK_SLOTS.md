# Pocket v1.39 — Quick Slots (Numpad 1–9)

A compact, local-first extension of Clipboard **Text** history. No new
Clipboard panel, row, button, or resized control is required.

## Use

| Action | Windows global shortcut |
| --- | --- |
| Paste Quick Slot 1–9 to the focused application | `Ctrl+Alt+Numpad1` through `Ctrl+Alt+Numpad9` |
| Save selection or current clipboard text in Quick Slot 1–9 | `Ctrl+Alt+Shift+Numpad1` through `Ctrl+Alt+Shift+Numpad9` |

Use the **right-side number pad with Num Lock enabled**, not the digits
above the alphabet. All bindings are registered with Win32 `RegisterHotKey`
and only respond to their own combination. If Windows or another application
has already registered a combination, that binding may not be available.

### Saving

1. Select text in the current application and press a **save** shortcut.
2. Pocket borrows the Windows clipboard briefly to copy the selection,
   then restores its original data (including non-text formats).
3. If no fresh nonempty selected text was copied, Pocket falls back to
   **the text that was in the clipboard before the shortcut**.
4. The slot is persisted locally. No upload or DashDash call occurs.
5. When the destination slot is already occupied by different text, Pocket
   asks for confirmation before replacing it. Declining leaves it unchanged.

To avoid accidental storage of secrets, recognizable sensitive text is
rejected while Pocket's Sensitive Text Filter is enabled.

### Pasting

Press `Ctrl+Alt+NumpadN` while focused in a target application. Pocket
temporarily places the chosen text into the Windows clipboard, issues
`Ctrl+V` to the original foreground window, and attempts to restore the
previous multi-format clipboard contents. It does not leave the chosen
slot permanently replacing the user's original clipboard. Some elevated,
remote, or protected applications may refuse injected paste input; in
those cases, use Pocket's existing **Copy** action followed by manual
`Ctrl+V`.

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
