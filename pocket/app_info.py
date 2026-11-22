"""Pocket author credit and current application version.

Version 1.40 is shown inside the experimental Extra build and Settings.
The existing published stable 1.39.9 packages remain unchanged.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.40"


def version_label() -> str:
    return f"v{VERSION}"
