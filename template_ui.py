"""Tk dialogs for optional Pocket Smart Command Templates.

No new menu is needed. Normal, Mini and Dashboard invoke the same forms,
with scrolling for small screens; Extra Mini first opens Commands as before.
No generated CLI is executed, transmitted, or persisted.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import pocket_design as design
import smart_templates as smart

FONT = "Segoe UI"
PREVIEW_FONT = ("Consolas", 9)


def _window(app, title, *, width=590, height=640):
    c = design.colors(app.theme)
    popup = tk.Toplevel(app.root)
    popup.withdraw()
    popup.title("Pocket · " + title)
    popup.configure(bg=c["BG"])
    popup.minsize(390, 360)
    popup.resizable(True, True)
    screen_w = popup.winfo_screenwidth()
    screen_h = popup.winfo_screenheight()
    width = min(width, max(390, screen_w - 50))
    height = min(height, max(360, screen_h - 100))
    x = max(0, min(app.root.winfo_rootx() + 25, screen_w - width - 15))
    y = max(0, min(app.root.winfo_rooty() + 40, screen_h - height - 55))
    popup.geometry(f"{width}x{height}+{x}+{y}")
    popup.transient(app.root)
    app._modal = True
    def close(*_):
        try:
            if popup.winfo_exists():
                popup.grab_release()
                popup.destroy()
        except tk.TclError:
            pass
        app._modal = False
    popup.protocol("WM_DELETE_WINDOW", close)
    popup.bind("<Escape>", close)
    popup.deiconify()
    popup.grab_set()
    return popup, c, close


def _text(parent, caption, c, *, size=9, bold=False, muted=False, wrap=480):
    label = tk.Label(parent, text=caption, bg=c["BG"],
                     fg=c["MUTED"] if muted else c["WHITE"],
                     font=(FONT, size, "bold" if bold else "normal"),
                     anchor="w", justify="left", wraplength=wrap)
    label.pack(anchor="w", fill="x", pady=(2, 5))
    return label


def _scroll_form(parent, c):
    outer = tk.Frame(parent, bg=c["BG"])
    outer.pack(fill="both", expand=True)
    canvas = tk.Canvas(outer, bg=c["BG"], bd=0, highlightthickness=0)
    scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                           style="Pocket.Vertical.TScrollbar")
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    body = tk.Frame(canvas, bg=c["BG"])
    window = canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(window, width=e.width))
    def wheel(event):
        canvas.yview_scroll(-int(event.delta / 120) if event.delta else 0, "units")
    canvas.bind("<MouseWheel>", wheel)
    body.bind("<MouseWheel>", wheel)
    return body


def _read_box(widget):
    return widget.get("1.0", "end-1c")


def _status(parent, c, message):
    """Small inline validation/status line; avoid blocking popups for mistakes."""
    label = tk.Label(parent, text=message, bg=c["BG"], fg=c["MUTED"],
                     font=(FONT, 9), anchor="w", justify="left",
                     wraplength=490)
    label.pack(fill="x", pady=(4, 6))
    return label


def _input_hint(kind):
    return {
        "ipv4": "e.g. 192.0.2.10",
        "ipv6": "e.g. 2001:db8::10",
        "cidr": "e.g. 192.0.2.0/24",
        "ipv6_cidr": "e.g. 2001:db8::/64",
        "vlan": "1–4094",
        "port": "1–65535",
        "interface": "e.g. ge-0/0/1",
        "vrf": "Enter VRF name",
        "mac": "e.g. aa:bb:cc:dd:ee:ff",
        "integer": "Enter a whole number",
        "text": "Enter a value",
    }.get(kind, "Select an option")


def open_editor(app, row, *, on_changed):
    """Simple by default: command text, Refresh, field count, Save.

    Advanced field types/choice values are preserved, but hidden until the user
    explicitly selects Field options. Refresh always collapses those controls.
    """
    popup, c, close = _window(app, "Smart Template", width=570, height=530)
    shell = tk.Frame(popup, bg=c["BG"])
    shell.pack(fill="both", expand=True, padx=18, pady=(15, 12))

    _text(shell, "Create a Smart Template", c, size=14, bold=True)
    _text(shell, f"{row['machine']}  ·  {row['description'][:88]}", c, muted=True)
    state = smart.template_state(row)
    suggestion = smart.suggest_template(row["command"])
    # A stale template is still useful to *review*; never use it to generate
    # until explicitly reapproved with the new original command.
    existing = row.get("template") if isinstance(row.get("template"), dict) else None
    selected = existing if existing and isinstance(existing.get("format"), str) else suggestion
    if state == "needs_review":
        _text(shell, "The original command changed. Check the format before saving again.",
              c, muted=True, wrap=505)
    else:
        _text(shell, "Replace variable parts with {{FIELD_NAME}}. "
              "Only reviewed templates are saved.", c, muted=True, wrap=505)

    form = _scroll_form(shell, c)
    _text(form, "ORIGINAL COMMAND", c, size=8, bold=True)
    original_box = tk.Text(form, bg=c["PANEL"], fg=c["SECONDARY"],
                           wrap="word", height=min(4, max(2, row["command"].count("\n") + 2)),
                           font=PREVIEW_FONT, bd=0, padx=10, pady=8,
                           takefocus=False)
    original_box.insert("1.0", row["command"])
    original_box.configure(state="disabled")
    original_box.pack(fill="x", pady=(0, 11))

    _text(form, "TEMPLATE FORMAT", c, size=9, bold=True)
    fmt = tk.Text(form, bg=c["INPUT"], fg=c["WHITE"], insertbackground=c["ACCENT"],
                  selectbackground=c["ACCENT_DARK"], wrap="word", height=4,
                  font=PREVIEW_FONT, bd=0, padx=10, pady=8, undo=True,
                  highlightthickness=1, highlightbackground=c["BORDER"],
                  highlightcolor=c["ACCENT"])
    fmt.insert("1.0", selected["format"] if selected else row["command"])
    fmt.pack(fill="x", pady=(0, 5))
    _text(form, "Example: execute ping {{TARGET_IP}}", c, muted=True)

    count_card = tk.Frame(form, bg=c["PANEL"], highlightthickness=1,
                          highlightbackground=c["BORDER"])
    count_card.pack(fill="x", pady=(12, 5))
    count_label = tk.Label(count_card, bg=c["PANEL"], fg=c["WHITE"],
                           font=(FONT, 12, "bold"), anchor="w", padx=12, pady=12)
    count_label.pack(side="left", fill="x", expand=True)
    count_hint = tk.Label(count_card, text="Click Refresh after editing",
                          bg=c["PANEL"], fg=c["MUTED"], font=(FONT, 8),
                          padx=10, anchor="e")
    count_hint.pack(side="right")

    # Details are never drawn after Refresh. Users can reveal advanced options
    # deliberately, and older labels/types/choices remain intact.
    field_source = [dict(field) for field in (selected or {}).get("fields", [])
                    if isinstance(field, dict)]
    active_widgets = {}
    advanced_area = tk.Frame(form, bg=c["BG"])
    advanced_open = False
    advanced_btn = None

    def collect_changes():
        nonlocal field_source
        if not active_widgets:
            return
        updates = []
        for name, (label_var, type_var, choices_var) in active_widgets.items():
            item = {"name": name, "label": label_var.get().strip(),
                    "type": type_var.get()}
            if item["type"] == "choice":
                item["options"] = [v.strip() for v in choices_var.get().split("|")
                                   if v.strip()]
            updates.append(item)
        field_source = updates

    def hide_advanced():
        nonlocal advanced_open
        collect_changes()
        for widget in advanced_area.winfo_children():
            widget.destroy()
        active_widgets.clear()
        advanced_area.pack_forget()
        advanced_open = False
        advanced_btn.configure(text="Field options ▾")

    def show_advanced():
        nonlocal advanced_open
        if advanced_open:
            hide_advanced()
            return
        fields = smart.default_fields(_read_box(fmt), field_source)
        if not fields:
            return
        advanced_open = True
        advanced_btn.configure(text="Field options ▴")
        advanced_area.pack(fill="x", pady=(5, 5))
        _text(advanced_area, "Optional: adjust field labels, validation, or choices.",
              c, muted=True)
        for field in fields:
            item = tk.Frame(advanced_area, bg=c["PANEL"],
                            highlightthickness=1, highlightbackground=c["BORDER"])
            item.pack(fill="x", pady=4)
            tk.Label(item, text="{{" + field["name"] + "}}", bg=c["PANEL"],
                     fg=c["ACCENT"], font=("Consolas", 9, "bold"),
                     anchor="w").pack(anchor="w", padx=10, pady=(9, 3))
            line = tk.Frame(item, bg=c["PANEL"])
            line.pack(fill="x", padx=10, pady=(0, 7))
            label_var = tk.StringVar(value=field["label"])
            label_entry = design.entry(line, label_var, app.theme, compact=True)
            label_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 7))
            type_var = tk.StringVar(value=field["type"])
            picker = ttk.Combobox(line, textvariable=type_var,
                                   values=smart.FIELD_TYPES, state="readonly",
                                   width=13, style="Pocket.TCombobox")
            picker.pack(side="right")
            choices_var = tk.StringVar(value=" | ".join(field.get("options", [])))
            option_entry = design.entry(item, choices_var, app.theme, compact=True)
            option_entry.pack(fill="x", padx=10, pady=(0, 7), ipady=5)
            def update_choice(*_, v=type_var, widget=option_entry):
                widget.configure(state="normal" if v.get() == "choice" else "disabled")
            type_var.trace_add("write", update_choice)
            update_choice()
            active_widgets[field["name"]] = (label_var, type_var, choices_var)
        _text(advanced_area, "Choice type: separate options with |", c, muted=True)

    controls = tk.Frame(form, bg=c["BG"])
    controls.pack(fill="x", pady=(7, 5))
    refresh = design.button(controls, "↻  Refresh fields", lambda: refresh_count(),
                            app.theme, primary=True, compact=True)
    refresh.pack(side="left")
    advanced_btn = design.button(controls, "Field options ▾", show_advanced,
                                 app.theme, compact=True)
    advanced_btn.pack(side="right")

    def refresh_count():
        hide_advanced()
        fields = smart.default_fields(_read_box(fmt), field_source)
        number = len(fields)
        count_label.configure(
            text=f"{number} field{'s' if number != 1 else ''} detected",
            fg=c["ACCENT"] if number else c["NOTICE"])
        count_hint.configure(text="Ready to save" if number else "Add {{NAME}} to the format")
        # No large field cards are displayed here — only the number.
        advanced_btn.configure(state="normal" if number else "disabled")
        return fields

    def format_changed(_event=None):
        if fmt.edit_modified():
            count_hint.configure(text="Changes pending · Refresh")
            fmt.edit_modified(False)
    fmt.bind("<<Modified>>", format_changed)
    refresh_count()

    footer = tk.Frame(shell, bg=c["BG"])
    footer.pack(side="bottom", fill="x", pady=(10, 0))
    feedback = _status(footer, c, "Templates are optional. The original command is unchanged.")

    def save():
        # Save is safe even if the user forgot Refresh: refresh definitions from
        # the CURRENT format and preserve any optional advanced configuration.
        collect_changes()
        fields = smart.default_fields(_read_box(fmt), field_source)
        try:
            metadata = smart.validate_template(
                {"format": _read_box(fmt), "fields": fields}, row["command"])
            app._save_smart_template(row, metadata)
        except (ValueError, OSError, KeyError) as exc:
            feedback.configure(text=str(exc), fg=c["DANGER"])
            return
        close()
        on_changed()

    def remove():
        if not isinstance(row.get("template"), dict):
            close()
            return
        if not messagebox.askyesno(
                "Remove template",
                "Remove this template? The original command stays unchanged.",
                parent=popup):
            return
        try:
            app._save_smart_template(row, None)
        except (ValueError, OSError, KeyError) as exc:
            feedback.configure(text=str(exc), fg=c["DANGER"])
            return
        close()
        on_changed()

    buttons = tk.Frame(footer, bg=c["BG"])
    buttons.pack(fill="x", pady=(3, 0))
    design.button(buttons, "Save template", save, app.theme,
                  primary=True).pack(side="right")
    design.button(buttons, "Cancel", close, app.theme).pack(side="right", padx=7)
    if isinstance(row.get("template"), dict):
        design.button(buttons, "Remove", remove, app.theme,
                      compact=True, destructive=True).pack(side="left")
    fmt.focus_set()


def open_filler(app, row, *, on_copy):
    """Simple fill screen: inputs, live read-only preview, sticky Copy button."""
    if smart.template_state(row) != "configured":
        raise ValueError("Approve or repair this template before using it.")
    meta = smart.validate_template(row["template"], row["command"])
    height = min(690, 330 + 66 * len(meta["fields"]))
    popup, c, close = _window(app, "Fill Smart Template", width=510, height=height)
    shell = tk.Frame(popup, bg=c["BG"])
    shell.pack(fill="both", expand=True, padx=18, pady=(16, 13))
    _text(shell, "Fill in your command", c, bold=True, size=14)
    _text(shell, f"{row['machine']}  ·  {row['description'][:86]}", c, muted=True)

    # Sticky bottom action: remains visible when many fields require scrolling.
    footer = tk.Frame(shell, bg=c["BG"])
    footer.pack(side="bottom", fill="x", pady=(10, 0))
    action_line = tk.Frame(footer, bg=c["BG"])
    action_line.pack(fill="x")
    status = _status(footer, c, "Fill the fields to enable copying.")
    # Pack status above controls while leaving the action bar at the bottom.
    action_line.pack_forget()
    action_line.pack(side="bottom", fill="x", pady=(2, 0))

    form = _scroll_form(shell, c)
    vars_by_name = {}
    first_widget = None
    for index, field in enumerate(meta["fields"], start=1):
        name = field["name"]
        _text(form, f"{index}.  {field['label']}", c, size=10, bold=True)
        variable = tk.StringVar()
        if field["type"] == "choice":
            widget = ttk.Combobox(form, style="Pocket.TCombobox",
                                   textvariable=variable, values=field["options"],
                                   state="readonly")
        else:
            widget = design.entry(form, variable, app.theme)
        widget.pack(fill="x", ipady=5, pady=(0, 13))
        if field["type"] != "choice":
            widget.insert(0, "")
        vars_by_name[name] = variable
        if first_widget is None:
            first_widget = widget

    _text(form, "COMMAND PREVIEW", c, size=8, bold=True)
    preview = tk.Text(form, height=4, bg=c["PANEL"], fg=c["WHITE"],
                      selectbackground=c["ACCENT_DARK"], font=PREVIEW_FONT,
                      wrap="word", bd=0, padx=10, pady=9, takefocus=False)
    preview.pack(fill="x", pady=(0, 10))
    preview.configure(state="disabled")

    def values():
        return {name: var.get() for name, var in vars_by_name.items()}

    def update(*_):
        try:
            result = smart.render_template(row, values())
            error = ""
        except ValueError as exc:
            result = smart.TOKEN.sub(
                lambda m: values().get(m.group(1)) or m.group(0), meta["format"])
            error = str(exc)
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", result)
        preview.configure(state="disabled")
        copy_btn.configure(state="disabled" if error else "normal")
        if error:
            status.configure(text="Enter valid values to enable Copy.", fg=c["MUTED"])
        else:
            status.configure(text="Ready to copy · Pocket never executes commands",
                             fg=c["ACCENT"])

    def copy():
        try:
            generated = smart.render_template(row, values())
        except ValueError as exc:
            status.configure(text=str(exc), fg=c["DANGER"])
            return
        try:
            on_copy(generated, row["id"])
        except (ValueError, OSError, tk.TclError) as exc:
            status.configure(text=f"Could not copy: {exc}", fg=c["DANGER"])
            return
        close()

    design.button(action_line, "Cancel", close, app.theme,
                  compact=True).pack(side="left")
    copy_btn = design.button(action_line, "Copy command", copy,
                             app.theme, primary=True)
    copy_btn.pack(side="right", fill="x", expand=True, padx=(9, 0))

    for variable in vars_by_name.values():
        variable.trace_add("write", update)
    update()
    if first_widget is not None:
        first_widget.focus_set()
