"""Offline English/Hebrew *keyboard-position* conversion, not translation.

Port of DashDash src/utils.js keyboardTranslate, using the same Israel
English-QWERTY/Hebrew physical-key mapping. Deliberately preserves digits,
whitespace, unmapped punctuation and line endings. No network calls and no
text persistence.
"""
from __future__ import annotations

ENGLISH_TO_HEBREW = {
    "q": "/", "w": "'", "e": "ק", "r": "ר", "t": "א",
    "y": "ט", "u": "ו", "i": "ן", "o": "ם", "p": "פ",
    "[": "]", "]": "[",
    "a": "ש", "s": "ד", "d": "ג", "f": "כ", "g": "ע",
    "h": "י", "j": "ח", "k": "ל", "l": "ך", ";": "ף",
    "'": ",",
    "z": "ז", "x": "ס", "c": "ב", "v": "ה", "b": "נ",
    "n": "מ", "m": "צ", ",": "ת", ".": "ץ", "/": ".",
}
HEBREW_TO_ENGLISH = {v: k for k, v in ENGLISH_TO_HEBREW.items()}


def convert(text: str) -> str:
    """Apply DashDash's bidirectional per-character keyboard layout mapping."""
    if not isinstance(text, str):
        raise TypeError("Clipboard text must be a string.")
    return "".join(
        ENGLISH_TO_HEBREW.get(character,
                             ENGLISH_TO_HEBREW.get(character.lower(),
                                                   HEBREW_TO_ENGLISH.get(character, character)))
        for character in text
    )
