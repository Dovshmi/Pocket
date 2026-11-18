"""Reset only Pocket preferences, never notes, links, CLI data or clipboard."""
from __future__ import annotations
from copy import deepcopy

RESET_GROUPS = (
    ("appearance", "Appearance & layouts"),
    ("menus", "Visible menus & launcher"),
    ("keyboard", "Keyboard & hotkeys"),
    ("clipboard", "Clipboard preferences"),
    ("network", "Network connection"),
)
SETTINGS_FIELDS = {
    "appearance": ("display_mode",),
    "menus": ("visible_tabs", "reminders_menu_configured",
              "extra_mini_enabled", "extra_mini_tiles"),
    "keyboard": ("convert_enabled", "convert_mode", "quick_slots_enabled",
                 "quick_slots_paste_prefix", "quick_slots_copy_prefix",
                  "quick_slots_save_mode", "quick_slots_paste_mode",
                  "quick_slots_notification_mode"),
    "clipboard": ("clipboard_paused", "clipboard_sensitive_filter",
                  "clipboard_image_limit", "clipboard_storage",
                  "clipboard_days", "clipboard_autodelete_days",
                  "clipboard_text_display_limit", "clipboard_db_image_display_limit"),
    "network": ("use_windows_proxy",),
}


def reset_preferences(current, defaults, selected):
    """Return a new profile with only chosen preference groups reset."""
    choices = set(selected)
    if not choices or choices - {key for key, _ in RESET_GROUPS}:
        raise ValueError("Select valid settings groups to reset")
    result = deepcopy(current)
    old_settings = result.get("settings", {})
    default_settings = defaults.get("settings", {})
    if not isinstance(old_settings, dict) or not isinstance(default_settings, dict):
        raise ValueError("Invalid settings")
    for group in choices:
        for key in SETTINGS_FIELDS[group]:
            if key in default_settings:
                old_settings[key] = deepcopy(default_settings[key])
    if "appearance" in choices:
        result["theme"] = deepcopy(defaults.get("theme", "blue"))
        for key in ("window_position", "window_positions"):
            if key in defaults:
                result[key] = deepcopy(defaults[key])
    if "menus" in choices:
        for key in ("extra_mini_pages", "extra_mini_page"):
            if key in defaults:
                result[key] = deepcopy(defaults[key])
    if "keyboard" in choices:
        for key in ("hotkey", "convert_hotkey"):
            if key in defaults:
                result[key] = deepcopy(defaults[key])
    return result
