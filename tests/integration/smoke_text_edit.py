"""Real Tk shortcut and context-menu smoke test (Windows or Linux/Xvfb)."""
import tkinter as tk

from pocket import text_editing


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def trigger(root, widget, sequence):
    widget.focus_force()
    root.update()
    widget.event_generate(sequence, when="tail")
    root.update()


def main():
    root = tk.Tk()
    root.title("Pocket text-edit smoke")
    root.geometry("480x240+90+90")
    menus, focused = [], []
    try:
        text_editing.install(root, lambda e: menus.append(e.widget),
                             lambda e: focused.append(e.widget))
        entry = tk.Entry(root)
        entry.pack(fill="x")
        entry.insert(0, "Pocket clipboard text")
        editor = tk.Text(root, height=4, undo=True)
        editor.pack(fill="both", expand=True)
        editor.insert("1.0", "Two lines\nOf editable notes")
        root.update()

        trigger(root, entry, "<Control-a>")
        check(entry.selection_present(), "Entry Control+A must select the text")
        trigger(root, entry, "<Control-c>")
        check(root.clipboard_get() == "Pocket clipboard text", "Entry Control+C must copy")
        trigger(root, entry, "<Control-x>")
        check(entry.get() == "", "Entry Control+X must cut selected text")
        trigger(root, entry, "<Control-v>")
        check(entry.get() == "Pocket clipboard text", "Entry Control+V must paste")

        trigger(root, editor, "<Control-a>")
        check(bool(editor.tag_ranges("sel")), "Text Control+A must select all")
        trigger(root, editor, "<Control-c>")
        check(root.clipboard_get() == "Two lines\nOf editable notes",
              "Text Control+C must copy multiline data")

        entry.event_generate("<Button-3>", x=8, y=8, when="tail")
        root.update()
        check(menus and menus[-1] is entry, "Plain entry must get fallback menu")
        menu = text_editing.make_menu(
            root, entry,
            {"PANEL": "#242738", "WHITE": "#FFFFFF", "MUTED": "#999999",
             "ACCENT_DARK": "#45486A"},
            lambda _action: None)
        check(menu.index("end") >= 4, "Context menu must contain editing actions")
        menu.destroy()
        editor.bind("<Button-3>", lambda _event: "break")
        before = len(menus)
        editor.event_generate("<Button-3>", x=8, y=8, when="tail")
        root.update()
        check(len(menus) == before, "Existing Text right-click menu must be preserved")
        print("PASS: Tk Entry and Text Ctrl+A/C/X/V, menu and existing context bindings")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
