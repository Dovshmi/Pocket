"""Windows-only integration: actual embedded Win32 input HWNDs and live data."""
from pathlib import Path
import ctypes
import sys
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import native_inputs


def require(ok, label):
    if not ok:
        raise AssertionError(label)


def run():
    root = tk.Tk()
    root.geometry("530x290+95+95")
    root.title("Pocket native inputs integration")
    var = tk.StringVar(value="Initial")
    try:
        title = native_inputs.Entry(
            root, textvariable=var, fg="#F3F4FA", bg="#161923",
            font=("Segoe UI", 11), highlightthickness=1)
        title.pack(fill="x", padx=12, pady=12, ipady=8)
        phone = native_inputs.Entry(root, font=("Segoe UI", 10),
                                    fg="#F3F4FA", bg="#161923")
        phone.pack(fill="x", padx=12, ipady=5)
        mac = native_inputs.Text(root, height=5, undo=True, wrap="none",
                                 bg="#161923", fg="#F3F4FA",
                                 font=("Consolas", 10))
        mac.pack(fill="both", expand=True, padx=12, pady=12)
        root.update()
        require(isinstance(title, tk.Entry) and isinstance(mac, tk.Text),
                "Widgets must retain Tk compatibility")
        require(title.get() == "Initial", "Initial value missing")

        if native_inputs.IS_WINDOWS:
            require(title.native_hwnd and phone.native_hwnd and mac.native_hwnd,
                    "Native EDIT and RichEdit HWNDs must be present, not fallback")
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetClassNameW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int)
            user32.GetClassNameW.restype = ctypes.c_int
            for widget, klass in ((title, "Edit"), (phone, "Edit"),
                                  (mac, "RICHEDIT50W")):
                buffer = ctypes.create_unicode_buffer(128)
                require(user32.GetClassNameW(
                    ctypes.c_void_p(widget.native_hwnd), buffer, 128) > 0,
                    "Native Windows control must have a class name")
                require(buffer.value.lower() == klass.lower(),
                        f"Expected Windows {klass}, got {buffer.value}")

            # The original Pocket layout uses Tk's compact field height and
            # additional ipady. Win32 EDIT must sit in the vertical center,
            # rather than rendering the text at the top of the whole widget.
            from ctypes import wintypes
            user32.GetWindowRect.argtypes = (
                ctypes.c_void_p, ctypes.POINTER(wintypes.RECT))
            user32.GetWindowRect.restype = ctypes.c_int

            def native_edit_gaps(widget):
                host_rect, child_rect = wintypes.RECT(), wintypes.RECT()
                require(user32.GetWindowRect(
                    ctypes.c_void_p(widget.winfo_id()),
                    ctypes.byref(host_rect)) != 0, "Tk field bounds are readable")
                require(user32.GetWindowRect(
                    ctypes.c_void_p(widget.native_hwnd),
                    ctypes.byref(child_rect)) != 0, "Win32 edit bounds are readable")
                return (child_rect.top - host_rect.top,
                        host_rect.bottom - child_rect.bottom,
                        host_rect.bottom - host_rect.top,
                        child_rect.bottom - child_rect.top)

            for widget in (title, phone):
                above, below, outer_height, inner_height = native_edit_gaps(widget)
                require(abs(above - below) <= 2,
                        "Single-line Win32 text must be vertically centered")
                require(inner_height <= outer_height,
                        "Native edit must fit inside the original Tk input field")
            require(native_edit_gaps(title)[3] < native_edit_gaps(title)[2] - 6,
                    "Extra Tk ipady must surround text, not enlarge native text row")

            title.focus_force()
            root.update()
            require(title.has_native_focus(), "Native Entry must get real Win32 focus")
            var.set("שלום Windows 123")
            root.update()
            require(title.get() == "שלום Windows 123",
                    "StringVar -> Win32 must support mixed Unicode")

            # Exercise the real VK_A handler with a Ctrl-down keyboard state,
            # not a simulated Tk <Control-a> event (the old false positive).
            state = (ctypes.c_ubyte * 256)()
            require(user32.GetKeyboardState(state) != 0, "Read Windows keyboard state")
            ctrl_state = (ctypes.c_ubyte * 256)(*state)
            ctrl_state[native_inputs.VK_CONTROL] |= 0x80
            try:
                require(user32.SetKeyboardState(ctrl_state) != 0,
                        "Set keyboard state for native Ctrl+A")
                title._send(native_inputs.EM_SETSEL, 0, 0)
                title._send(native_inputs.WM_KEYDOWN, ord("A"), 0)
                first, last = ctypes.c_uint32(), ctypes.c_uint32()
                title._send(native_inputs.EM_GETSEL,
                            ctypes.addressof(first), ctypes.addressof(last))
                require(first.value == 0 and last.value >= len("שלום Windows 123"),
                        "Native Ctrl+A must select the real Windows Edit content")
            finally:
                user32.SetKeyboardState(state)
            title._send(native_inputs.WM_COPY)
            require(root.clipboard_get() == "שלום Windows 123",
                    "Native Ctrl+C/WM_COPY must use Windows clipboard")
            title._send(native_inputs.WM_CUT)
            title.sync_native()
            require(title.get() == "" and var.get() == "",
                    "Native cut must immediately sync StringVar")
            title._send(native_inputs.WM_PASTE)
            title.sync_native()
            require(title.get() == "שלום Windows 123" and
                    var.get() == "שלום Windows 123",
                    "Native paste must sync StringVar")

            # Programmatic input remains Tk-compatible and updates HWND.
            title.delete(0, tk.END)
            title.insert(0, "updated")
            root.update()
            require(var.get() == "updated" and title.get() == "updated",
                    "Tk Entry insert/delete must update Win32 control")

            payload = "VLAN MAC Address Interface\n100 00:11:22:33:44:55 1/1/4"
            mac.insert("1.0", payload)
            root.update()
            require(mac.get("1.0", "end-1c") == payload,
                    "Tk Text insert must update Win32 RichEdit")
            # RichEdit requires a CHARFORMAT color; WM_CTLCOLOREDIT alone
            # produces the black-on-dark text regression reported in Pocket.
            from pocket.native_bidi import CHARFORMATW
            fmt = CHARFORMATW()
            fmt.cbSize = ctypes.sizeof(fmt)
            mac._send(0x043A, 0, ctypes.addressof(fmt))  # EM_GETCHARFORMAT
            require(fmt.crTextColor == mac._native_fg,
                    "Native RichEdit must display Pocket's configured text color")
            face, px, weight = title._native_font_metrics()
            require(px <= 18 and face, "Native font must remain compact at 100% DPI")
            native_clip = "200 AA:BB:CC:DD:EE:FF 1/1/5"
            root.clipboard_clear()
            root.clipboard_append(native_clip)
            mac.focus_force()
            root.update()
            require(mac.has_native_focus(), "RichEdit must take native keyboard focus")
            mac._send(native_inputs.EM_SETSEL, -1, -1)
            mac._send(native_inputs.WM_PASTE)
            mac.sync_native()
            require(native_clip in mac.get("1.0", "end-1c"),
                    "Real RichEdit must handle native clipboard paste")

            # Commands retains its own Ctrl+Enter callback via the Tk loop,
            # while native RichEdit handles all ordinary editor accelerators.
            copied = []
            mac.bind("<Control-Return>", lambda _ev: copied.append(True))
            # Run a deterministic native polling turn, rather than racing
            # the timer against a heavily loaded Windows CI virtual desktop.
            if mac._native_after is not None:
                mac.after_cancel(mac._native_after)
                mac._native_after = None
            mac._native_pending_ctrl_return = True
            mac._native_tick()
            root.update()
            require(copied == [True],
                    f"Native Ctrl+Enter must reach command action (got {copied})")
            mac.tag_add("sel", "1.0", "end-1c")
            start, end = ctypes.c_uint32(), ctypes.c_uint32()
            mac._send(native_inputs.EM_GETSEL,
                      ctypes.addressof(start), ctypes.addressof(end))
            require(end.value > start.value,
                    "Tk select-all action must select the real RichEdit contents")
            mac.mark_set("insert", "end-1c")
            mac._send(native_inputs.EM_GETSEL,
                      ctypes.addressof(start), ctypes.addressof(end))
            require(end.value == start.value,
                    "Tk command caret move must update the real native editor")

            long_table = "100 00:11:22:33:44:55 dynamic bridging 1/1/4\n" * 2500
            mac.delete("1.0", tk.END)
            mac.insert("1.0", long_table)
            require(mac.get("1.0", "end-1c") == long_table,
                    "Native RichEdit must not truncate full CLI tables over 64 KiB")

            # MAC output and Commands both embed native RichEdit without
            # a visible WS_VSCROLL. Verify the actual wheel event scrolls
            # overflowing content and leaves short content stationary.
            user32.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
            user32.GetWindowLongW.restype = ctypes.c_long
            command = native_inputs.Text(
                root, height=3, undo=True, wrap="word", bg="#161923",
                fg="#F3F4FA", font=("Consolas", 9), padx=6, pady=6)
            command.pack(fill="x", padx=12)
            command.insert("1.0", "show running-config\n" * 90)
            root.update()
            require(command.native_hwnd, "Command viewer must use native RichEdit")

            def visible_line(widget):
                return widget._send(native_inputs.EM_GETFIRSTVISIBLELINE)

            def wheel(widget, delta):
                # WM_MOUSEWHEEL's signed delta is carried in HIWORD(wParam).
                widget._send(native_inputs.WM_MOUSEWHEEL,
                             (delta & 0xFFFF) << 16)
                root.update()  # Process the queued native EM_LINESCROLL.

            for widget, label in ((mac, "MAC"), (command, "Commands")):
                style = user32.GetWindowLongW(ctypes.c_void_p(widget.native_hwnd), -16)
                require(not (style & 0x00200000),
                        f"{label} must not display a vertical scrollbar")
                widget._send(native_inputs.EM_LINESCROLL, 0, -32767)
                root.update()
                require(visible_line(widget) == 0,
                        f"{label} could not reset scroll to the top")
                wheel(widget, -60)
                require(visible_line(widget) == 0,
                        f"{label} must accumulate sub-notch wheel deltas")
                wheel(widget, -60)
                down = visible_line(widget)
                require(down > 0,
                        f"{label} must scroll down without a visible scrollbar")
                wheel(widget, 120)
                require(visible_line(widget) < down,
                        f"{label} must scroll up without a visible scrollbar")

            command.delete("1.0", tk.END)
            command.insert("1.0", "show interfaces terse")
            command._send(native_inputs.EM_LINESCROLL, 0, -32767)
            root.update()
            wheel(command, -120)
            require(visible_line(command) == 0,
                    "Short commands must not scroll when already fully visible")

            # A Windows child must never use its stock white popup menu.
            # WM_CONTEXTMENU is marshalled to the Tk widget's Pocket handler.
            posted = []
            phone.bind("<Button-3>", lambda event: posted.append(
                (event.x_root, event.y_root)))
            px, py = phone.winfo_rootx() + 9, phone.winfo_rooty() + 8
            lp = ((py & 0xffff) << 16) | (px & 0xffff)
            phone._send(native_inputs.WM_CONTEXTMENU, phone.native_hwnd, lp)
            import time
            time.sleep(0.08)
            root.update()
            require(bool(posted), "Native right-click must invoke Pocket menu event")
            require(abs(posted[0][0] - px) <= 2,
                    "Context menu must preserve screen position")
            root.clipboard_clear()
            root.clipboard_append("111")
            phone.native_action("paste")
            require(phone.get() == "111", "Pocket Paste must edit native field")
            phone.native_action("select_all")
            require(phone.native_has_selection(), "Pocket Select All must use HWND")
            phone.native_action("copy")
            require(root.clipboard_get() == "111", "Pocket Copy must use HWND")
            phone.native_action("cut")
            require(phone.get() == "", "Pocket Cut must use HWND")
            phone.native_action("undo")
            require(phone.get() == "111", "Pocket Undo must use HWND")

            hint = tk.StringVar(value="Search CLI / חיפוש פקודה")
            search = native_inputs.Entry(root, textvariable=hint,
                                         bg="#161923", fg="#737C90",
                                         font=("Segoe UI", 9))
            search.pack(fill="x")
            search.set_native_placeholder(
                "Search CLI / חיפוש פקודה", on_focus=lambda: hint.set(""))
            search.bind("<FocusIn>", lambda _ev: hint.set(""))
            root.update()
            search.focus_force()
            time.sleep(0.08)
            root.update()
            require(hint.get() == "" and search.get() == "",
                    "Search hint must vanish on native keyboard focus")
            phone.focus_force()
            root.update()
            require(phone.has_native_focus() and not mac.has_native_focus(),
                    "Native focus must move cleanly between controls")
            require(native_inputs.has_native_focus(),
                    "Popup auto-hide must recognize native focused input")
            native_inputs.sync_all_native()
        else:
            require(native_inputs.Entry is tk.Entry and native_inputs.Text is tk.Text,
                    "Linux must keep Tk fallback")

        print("PASS: Native Win32 EDIT/RichEdit HWND, focus, clipboard and model synchronization")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
