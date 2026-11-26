"""Pocket author credit and current application version."""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.42.0"


def version_label() -> str:
    # Show the familiar minor-release label while keeping semantic versioning
    # for build tools and package filenames.
    return f"v{VERSION[:-2]}" if VERSION.endswith(".0") else f"v{VERSION}"
