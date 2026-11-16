"""Pocket author credit and public release version.

Bump VERSION alongside the official Pocket release and Windows packages.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.37.0"


def version_label() -> str:
    return f"v{VERSION}"
