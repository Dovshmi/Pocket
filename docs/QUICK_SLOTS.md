# Pocket v1.39 — Quick Slots (Numpad 1–9)

A compact, local-first extension of Clipboard **Text** history. No new
Clipboard panel, row, button, or resized control is required.

## Use

Each Quick Slot has **two separate direct global shortcuts**, using the
right-hand number pad with **Num Lock ON**. There is no Save Mode and
**Numpad0 is not registered**.

| Action | Default global shortcut |
| --- | --- |
| Paste stored slot N | `Ctrl+Alt+Numpad1–9` |
| Save selected text to slot N | `Ctrl+Win+Numpad1–9` |

For example, to save a selected IP in slot 1, press
`Ctrl+Win+Numpad1`. To paste it later, press `Ctrl+Alt+Numpad1`.
The action is immediate: no second key sequence, mode timer, or extra
window is needed.

Windows can reserve some Win-key combinations. Pocket checks whether
all required shortcuts can be registered and preserves the existing
configuration if the new configuration fails.

## Settings

Open **Settings → Clipboard & privacy**:

* **Enable Quick Slots:** ON/OFF for both global shortcut groups and the
  numbered Clipboard list entries. Disabling does not delete values.
* **Paste shortcut prefix:** default `Ctrl+Alt`.
* **Save / Copy shortcut prefix:** default `Ctrl+Win`.

Each dropdown chooses **only modifier keys**: `Ctrl+Alt`, `Ctrl`,
`Ctrl+Win` or `Ctrl+Alt+Win`. The actual keys are always
**Numpad1–9**; their numbers cannot be changed in Settings.
Shift is intentionally not available because Windows can convert
Shift+Numpad digits into navigation key events.

Copy and paste cannot use the same modifier prefix. If a replacement
group conflicts with another application or Windows, the old working
group remains registered. The other group stays usable throughout.
Changes apply without restarting Pocket.

### Saving / copying

1. Highlight text in any foreground Windows application.
2. Press `Ctrl+Win+NumpadN` (or the configured Save prefix + NumpadN).
3. Pocket temporarily issues `Ctrl+C` to capture the selection.
4. If the application has no copyable selection, Pocket falls back to
   **text already in the Windows clipboard before this operation**.
5. Pocket restores the pre-existing clipboard data, when safe, and saves
   the chosen value in the numbered Quick Slot. No upload occurs.
6. Replacing an occupied slot asks for confirmation; displaced automatic
   Favorites are removed rather than accumulating.

The Sensitive Text Filter can reject recognized secret-looking text.
Do not store passwords or authentication tokens in Quick Slots.

### Pasting

Press `Ctrl+Alt+NumpadN` (or the configured Paste prefix + NumpadN)
while focused in the target Windows application. Pocket temporarily
places the stored value in the clipboard, issues `Ctrl+V` to the
original application, and attempts to restore the prior multi-format
clipboard contents.

Some elevated, remote, or protected applications refuse injected copy
or paste input; those applications may require ordinary manual copy/paste.

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
