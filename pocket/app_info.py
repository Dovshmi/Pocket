"""Pocket author credit and current application version.

The feature branch may show a development version before its official release.
Official stable v1.39.8 packages and download links remain unchanged.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.39.9"


def version_label() -> str:
    return f"v{VERSION}"
