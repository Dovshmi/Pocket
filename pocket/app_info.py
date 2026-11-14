"""Pocket public UI attribution and display version.

Keep the UI version synchronized with the latest published release when a
new official release is prepared. Current public stable release: v1.34.0.
Development branch builds can contain additional unreleased improvements.
"""

AUTHOR_CREDIT = "By. Rony Shmidov"
VERSION = "1.34.0"


def version_label() -> str:
    return f"v{VERSION}"
