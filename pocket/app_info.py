"""Pocket author credit and current application version.

Version 1.40 is shown inside the experimental Extra build and Settings.
The existing published stable 1.39.9 packages remain unchanged.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.40.0"


def version_label() -> str:
    # Show the familiar minor-release label while keeping semantic versioning
    # for build tools and package filenames.
    return f"v{VERSION[:-2]}" if VERSION.endswith(".0") else f"v{VERSION}"
