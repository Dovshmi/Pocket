"""Clipboard history safety policy for Pocket.

Heuristic matching is intentionally conservative and imperfect: protected
patterns are skipped, but no clipboard monitor can guarantee all secrets
will be recognized. No clipboard contents ever get written to disk.
"""
from __future__ import annotations
import re

_PATTERNS=(
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",re.I),
    re.compile(r"\b(?:Bearer\s+)[A-Za-z0-9_\-.~+/]{16,}",re.I),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(?:password|passwd|api[_ -]?key|client[_ -]?secret|access[_ -]?token)\s*[:=]\s*\S{4,}",re.I),
)

def should_capture(value, *, paused=False, sensitive_filter=True, max_length=20000):
    if paused or not isinstance(value,str) or not value.strip() or len(value)>max_length:
        return False
    if sensitive_filter and any(pattern.search(value) for pattern in _PATTERNS):
        return False
    return True
