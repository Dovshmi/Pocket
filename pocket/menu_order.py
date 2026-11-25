"""Persistent, safe menu order for Pocket's Mini/Normal/Dashboard navigation.

All menu slots are always represented, even when currently hidden. Settings
is reorderable; the special More/Less overflow control is never reorderable.
Older settings and backups without the preference retain the original order.
"""
from __future__ import annotations

DEFAULT_ORDER = (
    "notes", "links", "ports", "mac", "commands", "subnet",
    "clipboard", "reminders", "extra", "settings",
)
_LABELS = {
    "notes": "Notes", "links": "Links", "ports": "Ports", "mac": "MAC",
    "commands": "CLI", "subnet": "Subnet", "clipboard": "Clip",
    "reminders": "Remind", "extra": "Extra", "settings": "Settings",
}
LABELS = dict(_LABELS)


def normalize(raw):
    """Complete, duplicate-free order; ignore invalid values without guessing."""
    if not isinstance(raw, (list, tuple)):
        return list(DEFAULT_ORDER)
    ordered = []
    for key in raw:
        if isinstance(key, str) and key in DEFAULT_ORDER and key not in ordered:
            ordered.append(key)
    return ordered + [key for key in DEFAULT_ORDER if key not in ordered]


def enabled_order(raw_order, visible_tabs, *, include_settings=True):
    """Keep the saved position of hidden menus for when they're re-enabled."""
    allowed = set(visible_tabs)
    if include_settings:
        allowed.add("settings")
    return [key for key in normalize(raw_order) if key in allowed]


def move(raw_order, moving, target, *, after=False):
    """Move one icon before or after another, preserving all other positions."""
    result = normalize(raw_order)
    if moving not in result or target not in result or moving == target:
        return result
    result.remove(moving)
    result.insert(result.index(target) + int(after), moving)
    return result
