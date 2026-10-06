"""Repair text typed with the wrong keyboard layout (Thai Kedmanee <-> English QWERTY).

e.g. meaning "อุระกาวาท 2 ขวด" but forgetting to switch layout gives "v6itdk;km 2 -;f".
Number-only tokens are never converted, so counts typed on the number pad survive.
"""
from __future__ import annotations

import re
from typing import Iterable

# (QWERTY key, Kedmanee character) — unshifted rows, then shifted rows
_KEY_PAIRS = [
    ("`", "_"), ("1", "ๅ"), ("2", "/"), ("3", "-"), ("4", "ภ"), ("5", "ถ"), ("6", "ุ"),
    ("7", "ึ"), ("8", "ค"), ("9", "ต"), ("0", "จ"), ("-", "ข"), ("=", "ช"),
    ("q", "ๆ"), ("w", "ไ"), ("e", "ำ"), ("r", "พ"), ("t", "ะ"), ("y", "ั"), ("u", "ี"),
    ("i", "ร"), ("o", "น"), ("p", "ย"), ("[", "บ"), ("]", "ล"), ("\\", "ฃ"),
    ("a", "ฟ"), ("s", "ห"), ("d", "ก"), ("f", "ด"), ("g", "เ"), ("h", "้"), ("j", "่"),
    ("k", "า"), ("l", "ส"), (";", "ว"), ("'", "ง"),
    ("z", "ผ"), ("x", "ป"), ("c", "แ"), ("v", "อ"), ("b", "ิ"), ("n", "ื"), ("m", "ท"),
    (",", "ม"), (".", "ใ"), ("/", "ฝ"),
    ("~", "%"), ("!", "+"), ("@", "๑"), ("#", "๒"), ("$", "๓"), ("%", "๔"), ("^", "ู"),
    ("&", "฿"), ("*", "๕"), ("(", "๖"), (")", "๗"), ("_", "๘"), ("+", "๙"),
    ("Q", "๐"), ("W", '"'), ("E", "ฎ"), ("R", "ฑ"), ("T", "ธ"), ("Y", "ํ"), ("U", "๊"),
    ("I", "ณ"), ("O", "ฯ"), ("P", "ญ"), ("{", "ฐ"), ("}", ","), ("|", "ฅ"),
    ("A", "ฤ"), ("S", "ฆ"), ("D", "ฏ"), ("F", "โ"), ("G", "ฌ"), ("H", "็"), ("J", "๋"),
    ("K", "ษ"), ("L", "ศ"), (":", "ซ"), ('"', "."),
    ("Z", "("), ("X", ")"), ("C", "ฉ"), ("V", "ฮ"), ("B", "ฺ"), ("N", "์"), ("M", "?"),
    ("<", "ฒ"), (">", "ฬ"), ("?", "ฦ"),
]
EN_TO_TH: dict[str, str] = dict(_KEY_PAIRS)
# only Thai characters map back; ASCII produced by the Thai layout ("/", "-", …) stays ASCII
TH_TO_EN: dict[str, str] = {th: en for en, th in _KEY_PAIRS if not th.isascii()}

# count units staff may type after a number, in both languages
UNITS = (
    "ขวด", "ซอง", "ถุง", "กล่อง", "เล่ม", "ชิ้น", "แพ็ค", "กระปุก", "กระป๋อง", "ถุงผ้า", "ห่อ", "สเปรย์",
    "bottle", "pouch", "bag", "box", "book", "pack", "package", "pcs", "jar", "tin", "can", "tote", "spray", "wrap",
)

_SPLIT_RE = re.compile(r"(\s+)")
_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
_THAI_RE = re.compile("[" + chr(0x0E00) + "-" + chr(0x0E7F) + "]")  # the Thai Unicode block


def _convert(text: str, table: dict[str, str], needs: re.Pattern) -> str:
    out = []
    for token in _SPLIT_RE.split(text):
        if token.isdigit() or not needs.search(token):
            out.append(token)  # whitespace, plain numbers, or nothing to convert
        else:
            out.append("".join(table.get(ch, ch) for ch in token))
    return "".join(out)


def to_thai(text: str) -> str:
    """Read text as if it had been typed on the Thai layout."""
    return _convert(text, EN_TO_TH, _ASCII_LETTER_RE)


def to_english(text: str) -> str:
    """Read text as if it had been typed on the English layout."""
    return _convert(text, TH_TO_EN, _THAI_RE)


def fix_layout(text: str, vocabulary: Iterable[str]) -> str:
    """Swap layout only for words that become a known word (product name or unit) after swapping."""
    words = [w.casefold() for w in vocabulary]

    def known(token: str) -> bool:
        t = token.casefold()
        return len(t) >= 2 and any(t in w for w in words)

    out = []
    for token in _SPLIT_RE.split(text):
        if not token.strip() or token.isdigit() or known(token):
            out.append(token)
            continue
        for candidate in (to_thai(token), to_english(token)):
            if candidate != token and known(candidate):
                out.append(candidate)
                break
        else:
            out.append(token)
    return "".join(out)
