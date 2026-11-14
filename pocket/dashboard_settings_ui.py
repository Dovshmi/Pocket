"""Dashboard Settings adapter for Pocket's shared, responsive Preferences UI.

The shared settings builder provides Dashboard's two independent columns and
exposes dashboard_settings_controls for the existing GUI checks.
"""
from __future__ import annotations

from . import settings_ui


def build(app, parent):
    return settings_ui.build_settings(app, parent, wide=True)
