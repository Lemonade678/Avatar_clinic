"""Thai digits ๐–๙ -> 0–9 (phones with a Thai keyboard type these into number fields)."""
from __future__ import annotations

import re

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_WHOLE_NUMBER_RE = re.compile(r"-?\d+")


def to_ascii_digits(text: str) -> str:
    return text.translate(THAI_DIGITS)


def parse_count(raw: str) -> int | None:
    """A count typed into a form field: whole number >= 0, Thai digits allowed; None if invalid/blank."""
    text = to_ascii_digits(raw.strip())
    if not text or not _WHOLE_NUMBER_RE.fullmatch(text):
        return None
    value = int(text)
    return value if value >= 0 else None
