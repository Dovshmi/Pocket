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
            mac._native_pending_ctrl_return = True
            import time
            time.sleep(0.07)
            root.update()
            require(copied == [True], "Native Ctrl+Enter must reach command action")
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
