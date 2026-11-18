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
| Save selected text to slot N | `Ctrl+Alt+Win+Numpad1–9` |

For example, to save a selected IP in slot 1, press
`Ctrl+Alt+Win+Numpad1`. To paste it later, press `Ctrl+Alt+Numpad1`.
The action is immediate: no second key sequence, mode timer, or extra
window is needed.

Windows can reserve some Win-key combinations. Pocket checks whether
all required shortcuts can be registered and preserves the existing
configuration if the new configuration fails.

## Windows tray menu

Right-click the Pocket icon in the notification area to open **Open Pocket**,
**Open Settings**, **Create Backup**, **Restore Backup** or **Exit Pocket**.
These use the original Settings and Backup/Restore interfaces. They run locally
and do not require internet access.

## Settings

Open **Settings → Clipboard & privacy**:

* **Enable Quick Slots:** ON/OFF for both global shortcut groups and the
  numbered Clipboard list entries. Disabling does not delete values.
* **Quick Slot save behavior:** **Auto Copy Selection** (default) sends
  `Ctrl+C` to capture selected text in the focused app, using the existing
  Windows clipboard as a fallback if nothing is selected. **Use Current
  Clipboard** never sends `Ctrl+C`; first copy the text manually, then press
  the Quick Slot Save hotkey. It reads that clipboard text and saves it in
  the chosen slot. An empty/non-text clipboard is rejected. This setting
  is independent of Paste behavior.
* **Quick Slot paste behavior:** **Auto Paste** (default for existing and new
  users) inserts into the current application; **Copy to Clipboard** changes
  the Windows clipboard to the selected slot and waits for your ordinary
  `Ctrl+V`. The choice is saved across app restarts.
* **Paste shortcut prefix:** default `Ctrl+Alt`.
* **Save / Copy shortcut prefix:** default `Ctrl+Alt+Win`.

**The two behavior dropdowns are independent.** For example, you can
keep Auto Copy Selection enabled but set Paste to Copy to Clipboard
for programs where Hebrew only pastes correctly with a physical Ctrl+V.
Or select Use Current Clipboard for saving while keeping Auto Paste.

Each dropdown chooses **only modifier keys**: `Ctrl+Alt`, `Ctrl`,
`Ctrl+Win` or `Ctrl+Alt+Win`. The actual keys are always
**Numpad1–9**; their numbers cannot be changed in Settings.
Shift is intentionally not available because Windows can convert
Shift+Numpad digits into navigation key events.

The Quick Slot **Record** buttons are no longer shown in Settings.
Use the modifier dropdowns instead; Numpad1–9 always remain fixed.

Native Windows Quick Slot notifications use **Pocket · Copy [N]**,
**Pocket · Paste [N]**, or **Pocket · Unchanged [N]** as the title, with
no redundant Copy label for unchanged text. They put **only the text preview**
(up to 108 characters) in the message body, avoiding duplicated action words.
Copy-to-Clipboard mode still requires pressing Ctrl+V manually to paste.

Under **Settings → Clipboard & privacy → Quick Slot notifications**, choose
**Copy + Paste** (default), **Copy only**, **Paste only**, or **Off** using one
dropdown. This setting applies to both success and failure notices from Quick
Slots; unrelated notices (including Note reminders) are unchanged. The selected
mode is saved locally with other Quick Slot settings and is deliberately excluded
from portable backup along with other Quick Slot preferences. Text previews may
be visible in Windows notification history, so never store secrets in Quick Slots.

Copy and paste cannot use the same modifier prefix. If a replacement
group conflicts with another application or Windows, the old working
group remains registered. The other group stays usable throughout.
Changes apply without restarting Pocket.

### Saving / copying

1. Highlight text in any foreground Windows application.
2. Press `Ctrl+Alt+Win+NumpadN` (or the configured Save prefix + NumpadN).
3. Pocket waits for the configured Save shortcut to be released, then issues
   ordinary `Ctrl+C` to capture the selected text.
4. If the application has no copyable selection, Pocket falls back to
   **text already in the Windows clipboard before this operation**.
5. In **Auto Copy Selection** mode, the selected text is saved in the
   numbered Quick Slot **and remains in the Windows clipboard**, just like
   an ordinary Copy operation.
   This deliberately avoids an unreliable OLE restore while copying selected
   text. If there is no selection, the existing clipboard is unchanged.
   No upload occurs.
6. Replacing an occupied slot opens the original **native Windows Yes/No
   MessageBox**, not a custom Tkinter window. The compact text is:
   **Old text: preview**, then **↓**, then **New text: preview** on
   separate lines. The slot number is in the title; previews can show
   up to 30 characters each, allowing a little more room for the text.
   Windows determines the final dialog dimensions.
   No/Escape never changes the slot.
7. On Yes, the displaced OLD value is preserved in regular history **without
   a Pin**. If it already exists in today's history it is unpinned, not copied;
   if absent it is inserted as an unpinned entry. Applies to both RAM and
   DATABASE storage. A failed history write cancels the replacement, preserving
   the original slot. If the sensitive-text filter rejects the OLD value,
   replacement is blocked rather than silently discarding it.

**Use Current Clipboard mode:** instead of steps 1–5 above, copy text yourself
using `Ctrl+C` or another copy action, then press the slot's Save shortcut.
Pocket reads the current clipboard without sending an automatic copy
keystroke. No clipboard modification occurs during this read. Both Save
modes use the same replacement confirmation and privacy filter.

The Sensitive Text Filter can reject recognized secret-looking text.
Do not store passwords or authentication tokens in Quick Slots.

### Pasting

Press `Ctrl+Alt+NumpadN` (or the configured Paste prefix + NumpadN)
while focused in the target Windows application.

- **Auto Paste** (default) uses Unicode keyboard input for ASCII-only
  slots, leaving the existing clipboard untouched. For Hebrew, Arabic,
  accented text, emoji or other non-ASCII characters, it uses Windows
  `CF_UNICODETEXT` and sends `Ctrl+V` to the target instead. This prevents
  `?` replacement by applications that mishandle Unicode key injection.
  In that case the new text **remains in the clipboard** afterward, and
  the original clipboard is not restored. This avoids OLE
  `CloseClipboard Failed` errors.
- **Copy to Clipboard** makes the slot the current Windows clipboard text,
  without sending any paste shortcut. Press normal `Ctrl+V` to paste manually.
  The previous clipboard is intentionally replaced.

Some elevated, remote, or protected applications refuse injected keyboard
input. Use **Copy to Clipboard** in Settings for those applications.

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
  one-shot selection capture and clipboard-independent Unicode Auto Paste.
* `pocket/clipboard_gallery.py`: compact `[N]` badge in Listbox content,
  and a nine-item right-click submenu.
* `app.pyw`: local profile migration, replacement dialogs, background
  operations and tray hotkey registration. All Tk interactions remain
  on the Tk event thread.
* `tests/test_quick_slots.py`: headless model, clipboard, persistence,
  and replacement regressions.
* `tests/integration/smoke_dashboard_integration.py`: verifies the
  nine entries and unchanged text panel geometry.

Version 1.39.1 adds the optional clipboard-only mode and resilient
clipboard snapshot fallback.
