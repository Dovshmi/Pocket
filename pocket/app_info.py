"""Pocket author credit and current application version.

Version 1.40 is shown inside Pocket and Settings in the main source.
The previously published stable 1.39.9 packages remain available.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.40.0"


def version_label() -> str:
    # Show the familiar minor-release label while keeping semantic versioning
    # for build tools and package filenames.
    return f"v{VERSION[:-2]}" if VERSION.endswith(".0") else f"v{VERSION}"
