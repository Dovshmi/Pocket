"""Exercise compact replacement Toplevel on a real Tk display (Windows/Xvfb)."""
import tkinter as tk
from pocket import quick_slot_dialog


def run():
    root = tk.Tk()
    root.withdraw()
    try:
        for accepted in (False, True):
            found = []
            def press_choice():
                dialogs = [x for x in root.winfo_children()
                           if isinstance(x, tk.Toplevel)]
                assert len(dialogs) == 1, "Quick Slot dialog did not appear"
                dialog = dialogs[0]
                assert dialog.winfo_width() <= 420
                assert dialog.winfo_height() <= 200
                assert dialog.title() == "Replace Quick Slot [2]?"
                frames = [x for x in dialog.winfo_children()
                          if isinstance(x, tk.Frame)]
                assert frames, "Missing compact content row"
                body = frames[0]
                cells = [x for x in body.winfo_children()
                         if isinstance(x, tk.Frame)]
                assert len(cells) == 2
                left = min(cells, key=lambda x: x.winfo_rootx())
                right = max(cells, key=lambda x: x.winfo_rootx())
                left_text = [x.cget("text") for x in left.winfo_children()
                             if isinstance(x, tk.Label)]
                right_text = [x.cget("text") for x in right.winfo_children()
                              if isinstance(x, tk.Label)]
                assert left_text == ["NEW", "SVLAN 11"], left_text
                assert right_text == ["OLD", "SVLAN 1557"], right_text
                controls = frames[-1]
                buttons = [x for x in controls.winfo_children()
                           if isinstance(x, tk.Button)]
                pressed = next(b for b in buttons
                               if b.cget("text") == ("Yes" if accepted else "No"))
                pressed.invoke()
                found.append(True)
            root.after(160, press_choice)
            result = quick_slot_dialog.confirm_replace(
                root, "blue", 2, "SVLAN 1557", "SVLAN 11")
            assert result is accepted, result
            assert found
    finally:
        root.destroy()
    print("PASS: compact New -> Old slot popup; No and Yes work")


if __name__ == "__main__":
    run()
