"""Modal Settings panels for selective offline backup, restore and reset."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from . import portable_backup as pb
from . import settings_reset as sr
from . import icon_themes as themes
from . import command_store as cs


def _dialog(app, title, *, height=590):
    c = themes.palette(app.theme)
    window = tk.Toplevel(app.root)
    window.title("Pocket · " + title)
    window.configure(bg=c["BG"])
    window.resizable(True, True)
    # Fit on smaller work laptops, retaining enough vertical room for actions.
    screen_w = app.root.winfo_screenwidth()
    screen_h = app.root.winfo_screenheight()
    width = min(525, max(400, screen_w - 35))
    height = min(height, max(450, screen_h - 80))
    x = max(12, min(app.root.winfo_rootx() + 20, screen_w - width - 15))
    y = max(12, min(app.root.winfo_rooty() + 30, screen_h - height - 45))
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.transient(app.root)
    app._modal = True
    def close():
        try:
            window.grab_release()
        except tk.TclError:
            pass
        if window.winfo_exists():
            window.destroy()
        app._modal = False
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _e: close())
    return window, close, c


def _title(window, name, detail, c):
    tk.Label(window, text=name, fg=c["WHITE"], bg=c["BG"],
             font=("Segoe UI", 15, "bold"), anchor="w").pack(
                 fill="x", padx=19, pady=(17, 4))
    tk.Label(window, text=detail, fg=c["MUTED"], bg=c["BG"],
             font=("Segoe UI", 9), wraplength=474,
             justify="left", anchor="w").pack(fill="x", padx=19, pady=(0, 13))


def _categories(window, c, choices, initial, callback, *, available=None):
    """Show every category; missing/empty groups remain visible but disabled."""
    available = set(choices if available is None else available)
    options = {}
    area = tk.Frame(window, bg=c["PANEL"])
    area.pack(fill="both", padx=16, pady=(0, 7), expand=True)
    for key in choices:
        enabled = key in available
        value = tk.BooleanVar(value=enabled and key in initial)
        options[key] = value
        check = tk.Checkbutton(
            area, variable=value, text=pb.LABELS[key], command=callback,
            anchor="w", bg=c["PANEL"], fg=c["WHITE"],
            disabledforeground=c["MUTED"], selectcolor=c["INPUT"],
            activeforeground=c["ACCENT"], activebackground=c["PANEL"],
            state="normal" if enabled else "disabled",
            font=("Segoe UI", 9), padx=13, pady=4)
        check.pack(fill="x")
    def set_all(selected):
        for key, flag in options.items():
            flag.set(bool(selected and key in available))
        callback()
    toggles = tk.Frame(window, bg=c["BG"])
    toggles.pack(fill="x", padx=19, pady=(0, 7))
    tk.Button(toggles, text="Select available",
              command=lambda: set_all(True),
              bg=c["CARD"], fg=c["WHITE"], relief="flat").pack(side="left")
    tk.Button(toggles, text="Clear", command=lambda: set_all(False),
              bg=c["CARD"], fg=c["WHITE"], relief="flat").pack(side="left", padx=7)
    tk.Label(toggles, text="Dimmed = unavailable", bg=c["BG"],
             fg=c["MUTED"], font=("Segoe UI", 8)
             ).pack(side="right")
    return options


def _footer(window, c, primary, action, close):
    footer = tk.Frame(window, bg=c["BG"])
    footer.pack(fill="x", padx=19, pady=(6, 18))
    tk.Button(footer, text="Cancel", command=close, relief="flat",
              bg=c["CARD"], fg=c["WHITE"], padx=13, pady=8
              ).pack(side="right")
    tk.Button(footer, text=primary, command=action, relief="flat",
              bg=c["ACCENT"], fg=c["BG"], padx=13, pady=8
              ).pack(side="right", padx=(0, 8))


def create_backup(app):
    window, close, c = _dialog(app, "Create Backup")
    _title(window, "Create Backup",
           "Choose only what to transfer. Quick Slot contents and shortcuts "
           "are NEVER included. Clipboard RAM history cannot be backed up.", c)
    available = pb.available_export_categories(
        app.data, commands_path=app.commands_file,
        profile_dir=app.path.parent)
    options = _categories(window, c, pb.CATEGORIES, available,
                          lambda: None, available=available)
    tk.Label(window, text="The ZIP is local and NOT encrypted. "
             "CLI commands and clipboard history may contain sensitive data.",
             bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 8),
             wraplength=472, justify="left").pack(fill="x", padx=19, pady=(4, 12))

    def save():
        selected = [name for name, value in options.items() if value.get()]
        if not selected:
            messagebox.showwarning("Backup", "Select at least one category.",
                                   parent=window)
            return
        name = "Pocket-Backup-" + datetime.now().strftime("%Y-%m-%d_%H-%M") + ".zip"
        filename = filedialog.asksaveasfilename(
            parent=window, title="Save selected Pocket backup",
            initialfile=name, defaultextension=".zip",
            filetypes=[("Pocket ZIP backup", "*.zip")])
        if not filename:
            return
        try:
            app._flush_current_note()
            if app._write_now() is False:
                return
            pb.make_backup(
                filename, app.data, commands_path=app.commands_file,
                profile_dir=app.path.parent, selected=selected)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Backup failed", str(exc), parent=window)
            return
        messagebox.showinfo(
            "Backup created",
            "Saved selected categories to:\n" + str(filename) +
            "\n\nYou can open this ZIP using Restore Backup on another computer.",
            parent=window)
        close()
    _footer(window, c, "Save ZIP", save, close)
    window.grab_set()


def restore_backup(app):
    filename = filedialog.askopenfilename(
        parent=app.root, title="Choose a Pocket backup ZIP",
        filetypes=[("Pocket ZIP backup", "*.zip")])
    if not filename:
        return
    try:
        bundle = pb.read_backup(Path(filename))
    except (OSError, ValueError, TypeError) as exc:
        messagebox.showerror("Invalid backup", str(exc), parent=app.root)
        return
    window, close, c = _dialog(app, "Restore Backup", height=755)
    _title(window, "Restore Backup",
           "Choose categories and preview their changes. Merge keeps local "
           "items when IDs conflict; Replace overwrites only selected categories. "
           "Restoring Settings applies their selected values in either mode.", c)
    available = pb.available_restore_categories(
        bundle, commands_path=app.commands_file)
    method = tk.StringVar(value="merge")
    # Every restorable category is checked on entry, including Clipboard.
    # Missing groups stay visible but cannot be selected.

    def chosen():
        return [key for key, value in options.items() if value.get()]

    def preview():
        selected = chosen()
        if not selected:
            display_preview("Select at least one available category.")
            return
        try:
            current_commands = (cs.read_document(app.commands_file)
                                if "cli" in selected and app.commands_file else None)
            plan = pb.plan_restore(bundle, app.data, selected=selected,
                                   mode=method.get(), current_commands=current_commands)
            parts = []
            for group, counts in plan["report"].items():
                summary = ", ".join(f"{key}: {value}" for key, value in counts.items())
                parts.append(f"{pb.LABELS[group]} — {summary}")
            display_preview("\n".join(parts))
        except (ValueError, TypeError, OSError) as exc:
            display_preview("Cannot preview this selection: " + str(exc))

    options = _categories(window, c, pb.CATEGORIES, available, preview,
                          available=available)
    choice = tk.Frame(window, bg=c["BG"])
    choice.pack(fill="x", padx=19, pady=(0, 8))
    for value, text in (("merge", "Merge · keep existing conflicts"),
                        ("replace", "Replace · overwrite selected categories")):
        tk.Radiobutton(choice, text=text, variable=method, value=value,
                       command=preview, bg=c["BG"], fg=c["WHITE"],
                       selectcolor=c["INPUT"], activebackground=c["BG"],
                       activeforeground=c["WHITE"]).pack(anchor="w")
    tk.Label(window, text="RESTORE PREVIEW  ·  scroll to review all categories",
             bg=c["BG"], fg=c["MUTED"], font=("Segoe UI", 8),
             anchor="w").pack(fill="x", padx=19, pady=(0, 4))
    preview_panel = tk.Frame(window, bg=c["PANEL"], height=127)
    preview_panel.pack(fill="x", padx=16, pady=(0, 7))
    preview_panel.pack_propagate(False)
    # The preview is wheel-scrollable but intentionally has no visible
    # scrollbar; it must not steal horizontal space or leave a white strip.
    preview_text = tk.Text(
        preview_panel, wrap="word", height=6, width=1,
        bg=c["PANEL"], fg=c["SECONDARY"], relief="flat",
        bd=0, padx=9, pady=7, highlightthickness=0,
        font=("Segoe UI", 9), cursor="arrow", state="disabled")
    preview_text.pack(fill="both", expand=True)

    def scroll_preview(event):
        if getattr(event, "num", None) == 4:  # X11 wheel up
            direction, steps = -1, 3
        elif getattr(event, "num", None) == 5:  # X11 wheel down
            direction, steps = 1, 3
        else:
            delta = getattr(event, "delta", 0)
            if not delta:
                return "break"
            direction = -1 if delta > 0 else 1
            steps = max(1, abs(delta) // 120) * 3
        preview_text.yview_scroll(direction * steps, "units")
        return "break"

    preview_text.bind("<MouseWheel>", scroll_preview)
    preview_text.bind("<Button-4>", scroll_preview)
    preview_text.bind("<Button-5>", scroll_preview)
    def display_preview(content):
        preview_text.configure(state="normal")
        preview_text.delete("1.0", "end")
        preview_text.insert("1.0", content)
        preview_text.configure(state="disabled")
        preview_text.yview_moveto(0)

    tk.Label(window, text="A recovery ZIP is saved before changing local data. "
             "Quick Slots remain local and unchanged. Reopen Pocket afterward.",
             fg=c["MUTED"], bg=c["BG"], font=("Segoe UI", 8),
             wraplength=460, justify="left").pack(fill="x", padx=19)

    def apply():
        selected = chosen()
        if not selected:
            messagebox.showwarning("Restore", "Select at least one category.",
                                   parent=window)
            return
        try:
            app._flush_current_note()
            if app._write_now() is False:
                return
            preview()  # Regenerate against the just-saved state.
            current_commands = (cs.read_document(app.commands_file)
                                if "cli" in selected and app.commands_file else None)
            plan = pb.plan_restore(bundle, app.data, selected=selected,
                                   mode=method.get(), current_commands=current_commands)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Restore validation failed", str(exc), parent=window)
            return
        conflicts = sum(x.get("conflicts", 0) for x in plan["report"].values())
        warning = ("Existing items in selected categories will be overwritten."
                   if method.get() == "replace"
                   else "Conflicting IDs will retain the local item.")
        if not messagebox.askyesno(
                "Confirm Restore",
                f"Restore {len(selected)} selected categories?\n{warning}\n"
                f"Reported conflicts: {conflicts}\n\n"
                "Pocket will close after restoring. Reopen it to apply all settings.",
                parent=window):
            return
        try:
            safety, _report = pb.apply_restore(
                bundle, app.data, selected=selected, mode=method.get(),
                profile_path=app.path, commands_path=app.commands_file)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                "Restore failed", "The restore stopped:\n" + str(exc) +
                "\n\nIf files were partially changed, use the before-restore "
                "ZIP in Pocket's backups folder.", parent=window)
            return
        messagebox.showinfo("Restore completed",
                            "Selected data restored.\n\nSafety backup:\n" +
                            str(safety) + "\n\nPocket will now close. Reopen it.",
                            parent=window)
        close()
        app._exit_after_restore()

    _footer(window, c, "Restore selected", apply, close)
    preview()
    window.grab_set()


def reset_settings(app, default_data):
    window, close, c = _dialog(app, "Default Settings", height=455)
    _title(window, "Restore Default Settings",
           "Choose which preferences to reset. Notes, Links, CLI, Quick Slot "
           "contents and clipboard history will NOT be deleted.", c)
    options = {}
    box = tk.Frame(window, bg=c["PANEL"])
    box.pack(fill="x", padx=17, pady=(0, 10))
    for key, label in sr.RESET_GROUPS:
        var = tk.BooleanVar(value=True)
        options[key] = var
        tk.Checkbutton(
            box, text=label, variable=var, bg=c["PANEL"], fg=c["WHITE"],
            selectcolor=c["INPUT"], activebackground=c["PANEL"],
            activeforeground=c["ACCENT"], font=("Segoe UI", 10),
            anchor="w", padx=12, pady=5).pack(fill="x")

    def apply():
        chosen = [key for key, value in options.items() if value.get()]
        if not chosen:
            messagebox.showwarning("Default Settings", "Choose settings to reset.",
                                   parent=window)
            return
        if not messagebox.askyesno(
                "Confirm Settings Reset",
                "Restore factory defaults for these groups?\n\n" +
                "\n".join(sr.RESET_GROUPS[i][1]
                          for i, pair in enumerate(sr.RESET_GROUPS)
                          if pair[0] in chosen) +
                "\n\nSaved personal content will be preserved. Pocket will close.",
                parent=window):
            return
        try:
            app._flush_current_note()
            if app._write_now() is False:
                return
            updated = sr.reset_preferences(app.data, default_data(), chosen)
            data_path = Path(app.path)
            from . import data_recovery
            data_recovery.save_profile(data_path, updated)
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror("Reset failed", str(exc), parent=window)
            return
        messagebox.showinfo(
            "Default Settings restored",
            "Selected preferences reset. Reopen Pocket to apply the defaults.",
            parent=window)
        close()
        app._exit_after_restore()
    _footer(window, c, "Reset selected", apply, close)
    window.grab_set()
