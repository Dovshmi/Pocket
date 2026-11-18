"""Pocket author credit and current application version.

Bump VERSION alongside the official Pocket release and Windows packages.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.39.8"


def version_label() -> str:
    return f"v{VERSION}"
