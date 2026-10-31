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


def open_editor(app, row, *, on_changed):
    """Manually review suggestions, field metadata, and live format before save."""
    popup, c, close = _window(app, "Smart Template Editor", width=640, height=695)
    shell = tk.Frame(popup, bg=c["BG"])
    shell.pack(fill="both", expand=True, padx=18, pady=14)
    _text(shell, "SMART TEMPLATE EDITOR", c, size=13, bold=True)
    _text(shell, f"{row['machine']}  ·  {row['description'][:100]}", c, muted=True)
    state = smart.template_state(row)
    suggestion = smart.suggest_template(row["command"])
    original = row.get("template") if state == "configured" else None
    selected = original or suggestion
    if state == "needs_review":
        _text(shell, "This command changed since its template was saved. Review and save again before use.",
              c, muted=True, wrap=565)
    elif selected and selected.get("warnings"):
        _text(shell, "Suggestion only — review syntax carefully. No changes are automatic.",
              c, muted=True, wrap=565)
    else:
        _text(shell, "Define {{FIELD_NAME}} in the format, then choose each field's type.",
              c, muted=True, wrap=565)

    form = _scroll_form(shell, c)
    _text(form, "ORIGINAL COMMAND (READ ONLY)", c, size=8, bold=True)
    original_box = tk.Text(form, bg=c["PANEL"], fg=c["SECONDARY"], wrap="word",
                           height=min(5, max(2, row["command"].count("\n") + 2)),
                           font=PREVIEW_FONT, bd=0, padx=10, pady=8)
    original_box.insert("1.0", row["command"])
    original_box.configure(state="disabled")
    original_box.pack(fill="x", pady=(0, 12))

    _text(form, "TEMPLATE FORMAT  ·  Use {{FIELD_NAME}} for each input", c, size=8, bold=True)
    fmt = tk.Text(form, bg=c["INPUT"], fg=c["WHITE"], insertbackground=c["ACCENT"],
                  wrap="word", height=5, font=PREVIEW_FONT,
                  bd=0, padx=10, pady=8, undo=True, highlightthickness=1,
                  highlightbackground=c["BORDER"], highlightcolor=c["ACCENT"])
    fmt.insert("1.0", selected["format"] if selected else row["command"])
    fmt.pack(fill="x", pady=(0, 5))
    _text(form, "You can replace any fixed value or unclear marker manually. "
          "Use distinct names when two IPs have different meanings.", c, muted=True)

    fields_area = tk.Frame(form, bg=c["BG"])
    fields_area.pack(fill="x", pady=(10, 2))
    field_widgets = {}
    field_source = selected.get("fields", []) if selected else []

    def rebuild_fields():
        nonlocal field_source
        existing = []
        for name, (label_var, type_var, choices_var) in field_widgets.items():
            item = {"name": name, "label": label_var.get(),
                    "type": type_var.get()}
            if item["type"] == "choice":
                item["options"] = [x.strip() for x in choices_var.get().split("|") if x.strip()]
            existing.append(item)
        if existing:
            field_source = existing
        for widget in fields_area.winfo_children():
            widget.destroy()
        field_widgets.clear()
        current = _read_box(fmt)
        defaults = smart.default_fields(current, field_source)
        if not defaults:
            _text(fields_area, "No valid placeholders found. Use {{TARGET_IP}} to add one.",
                  c, muted=True)
            return
        _text(fields_area, f"FIELDS  ·  {len(defaults)} unique input(s)", c, size=9, bold=True)
        for field in defaults:
            name = field["name"]
            container = tk.Frame(fields_area, bg=c["PANEL"], highlightthickness=1,
                                 highlightbackground=c["BORDER"])
            container.pack(fill="x", pady=4)
            line = tk.Frame(container, bg=c["PANEL"])
            line.pack(fill="x", padx=9, pady=(9, 4))
            tk.Label(line, text="{{" + name + "}}", bg=c["PANEL"],
                     fg=c["ACCENT"], font=("Consolas", 9, "bold")).pack(side="left")
            tk.Label(line, text="Validation type", bg=c["PANEL"],
                     fg=c["MUTED"], font=(FONT, 8)).pack(side="right")
            controls = tk.Frame(container, bg=c["PANEL"])
            controls.pack(fill="x", padx=9, pady=(0, 5))
            label_var = tk.StringVar(value=field["label"])
            name_input = tk.Entry(controls, textvariable=label_var,
                                  bg=c["INPUT"], fg=c["WHITE"],
                                  insertbackground=c["WHITE"], bd=0,
                                  font=(FONT, 9))
            name_input.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 7))
            type_var = tk.StringVar(value=field["type"])
            picker = ttk.Combobox(controls, style="Pocket.TCombobox", textvariable=type_var,
                                   values=smart.FIELD_TYPES, state="readonly", width=13)
            picker.pack(side="right")
            choices_var = tk.StringVar(value=" | ".join(field.get("options", [])))
            option_entry = tk.Entry(container, textvariable=choices_var,
                                    bg=c["INPUT"], fg=c["WHITE"], bd=0,
                                    font=(FONT, 9), insertbackground=c["WHITE"])
            option_entry.pack(fill="x", padx=9, pady=(0, 8), ipady=5)
            option_entry.configure(state="normal" if field["type"] == "choice" else "disabled")
            def update_choice(*_, v=type_var, control=option_entry):
                control.configure(state="normal" if v.get() == "choice" else "disabled")
            type_var.trace_add("write", update_choice)
            field_widgets[name] = (label_var, type_var, choices_var)

    controls = tk.Frame(form, bg=c["BG"])
    controls.pack(fill="x", pady=(3, 8))
    design.button(controls, "Refresh fields from format", rebuild_fields, app.theme,
                  compact=True).pack(side="left")
    _text(form, "For Choice fields, separate allowed values with | (example: enable | disable).",
          c, muted=True)
    rebuild_fields()

    actions = tk.Frame(shell, bg=c["BG"])
    actions.pack(fill="x", pady=(10, 1))
    def current_template():
        rows = []
        for name, (label_var, type_var, choices_var) in field_widgets.items():
            row_meta = {"name": name, "label": label_var.get(), "type": type_var.get()}
            if row_meta["type"] == "choice":
                row_meta["options"] = [x.strip() for x in choices_var.get().split("|") if x.strip()]
            rows.append(row_meta)
        return smart.validate_template({"format": _read_box(fmt), "fields": rows},
                                       row["command"])
    def save():
        try:
            metadata = current_template()
            app._save_smart_template(row, metadata)
        except (ValueError, OSError, KeyError) as exc:
            messagebox.showwarning("Review template", str(exc), parent=popup)
            return
        close()
        on_changed()
    def remove():
        if not isinstance(row.get("template"), dict):
            close()
            return
        if not messagebox.askyesno("Remove template",
                    "Remove the saved Smart Template for this command?\n"
                    "The original command will remain unchanged.", parent=popup):
            return
        try:
            app._save_smart_template(row, None)
        except (ValueError, OSError, KeyError) as exc:
            messagebox.showwarning("Template not removed", str(exc), parent=popup)
            return
        close()
        on_changed()
    design.button(actions, "Save approved template", save, app.theme,
                  primary=True).pack(side="right")
    design.button(actions, "Cancel", close, app.theme).pack(side="right", padx=7)
    if isinstance(row.get("template"), dict):
        design.button(actions, "Remove", remove, app.theme,
                      compact=True).pack(side="left")


def open_filler(app, row, *, on_copy):
    """Template values are transient. Copy alone; never mutate command storage."""
    if smart.template_state(row) != "configured":
        raise ValueError("Approve or repair this template before using it.")
    meta = smart.validate_template(row["template"], row["command"])
    popup, c, close = _window(app, "Fill Smart Template", width=525,
                               height=min(690, 315 + 75 * len(meta["fields"])))
    shell = tk.Frame(popup, bg=c["BG"])
    shell.pack(fill="both", expand=True, padx=18, pady=13)
    _text(shell, "FILL & COPY COMMAND", c, bold=True, size=13)
    _text(shell, f"{row['machine']}  ·  {row['description'][:100]}", c, muted=True)
    _text(shell, "Values are not stored in history, preferences or your command library.",
          c, muted=True)
    form = _scroll_form(shell, c)
    vars_by_name = {}
    for field in meta["fields"]:
        _text(form, field["label"] + "  ·  " + field["type"], c, size=9, bold=True)
        var = tk.StringVar()
        if field["type"] == "choice":
            widget = ttk.Combobox(form, style="Pocket.TCombobox", textvariable=var,
                                   values=field["options"], state="readonly")
        else:
            widget = design.entry(form, var, app.theme)
        widget.pack(fill="x", ipady=4, pady=(0, 10))
        vars_by_name[field["name"]] = var
    _text(form, "GENERATED COMMAND  ·  READ ONLY", c, size=8, bold=True)
    preview = tk.Text(form, height=5, bg=c["PANEL"], fg=c["WHITE"],
                      font=PREVIEW_FONT, wrap="word", bd=0, padx=9, pady=9)
    preview.pack(fill="x", pady=(0, 5))
    preview.configure(state="disabled")
    feedback = _text(form, "Fill all fields to enable Copy.", c, muted=True)
    def update(*_):
        vals = {name: var.get() for name, var in vars_by_name.items()}
        try:
            output = smart.render_template(row, vals)
            error = ""
        except ValueError as exc:
            output = smart.TOKEN.sub(lambda m: vals.get(m.group(1)) or m.group(0), meta["format"])
            error = str(exc)
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", output)
        preview.configure(state="disabled")
        feedback.configure(text=error or "Ready to copy · Nothing is executed",
                           fg=c["MUTED"] if error else c["ACCENT"])
        copy_btn.configure(state="disabled" if error else "normal")
    actions = tk.Frame(shell, bg=c["BG"])
    actions.pack(fill="x", pady=(10, 0))
    def copy():
        try:
            result = smart.render_template(row,
                    {name: var.get() for name, var in vars_by_name.items()})
        except ValueError as exc:
            messagebox.showwarning("Check template values", str(exc), parent=popup)
            return
        on_copy(result, row["id"])
        close()
    copy_btn = design.button(actions, "Generate & Copy", copy, app.theme, primary=True)
    copy_btn.pack(side="right")
    design.button(actions, "Cancel", close, app.theme).pack(side="right", padx=(0, 7))
    for var in vars_by_name.values():
        var.trace_add("write", update)
    update()
