"""Turn spoken (or quickly typed) text into counts for the products of one slot, Thai or English.

"อุระกาวาท เก้า ขวด" -> {"HB0001": 9} · "mala two" -> {"HB0098": 2}
Speech-to-text often drops the spaces in Thai, so matching works on text with spaces removed.
"""
from __future__ import annotations

import re

from .keyboard import UNITS, fix_layout
from .thai_digits import THAI_DIGITS

_THAI_VALUES = {
    "ศูนย์": 0, "หนึ่ง": 1, "เอ็ด": 1, "สอง": 2, "ยี่": 2, "สาม": 3, "สี่": 4,
    "ห้า": 5, "หก": 6, "เจ็ด": 7, "แปด": 8, "เก้า": 9,
}
_THAI_TOKEN = "|".join(sorted([*_THAI_VALUES, "สิบ", "ร้อย"], key=len, reverse=True))
_THAI_NUMBER_RE = re.compile(f"(?:{_THAI_TOKEN})+")

_EN_UNITS = {
    w: i for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen".split()
    )
}
_EN_TENS = {w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), start=2)}
_EN_TOKEN = "|".join(sorted([*_EN_UNITS, *_EN_TENS, "hundred"], key=len, reverse=True))
_EN_NUMBER_RE = re.compile(f"(?:(?:{_EN_TOKEN})(?:and)?)+")
_DIGITS_RE = re.compile(r"\d+")
_NOISE_RE = re.compile(r"[\s\-_()\[\].,:;]+")


def parse_thai_number(word: str) -> int | None:
    if not _THAI_NUMBER_RE.fullmatch(word):
        return None
    total, current = 0, 0
    for token in re.findall(_THAI_TOKEN, word):
        if token == "ร้อย":
            total, current = total + (current or 1) * 100, 0
        elif token == "สิบ":
            total, current = total + (current or 1) * 10, 0
        else:
            current = _THAI_VALUES[token]
    return total + current


def parse_english_number(words: str) -> int | None:
    squashed = _NOISE_RE.sub("", words.casefold())
    if not _EN_NUMBER_RE.fullmatch(squashed):
        return None
    total = 0
    for token in re.findall(_EN_TOKEN, squashed):
        if token == "hundred":
            total = (total or 1) * 100
        else:
            total += _EN_UNITS.get(token, 0) + _EN_TENS.get(token, 0)
    return total


def _squash(text: str) -> str:
    return _NOISE_RE.sub("", text.casefold().translate(THAI_DIGITS))


def _aliases(sku: str, name: str) -> set[str]:
    names = {name, re.sub(r"\([^)]*\)", "", name), sku}  # "มะเร็งปอด(ต้ม)" is often said as "มะเร็งปอด"
    return {a for a in (_squash(n) for n in names) if len(a) >= 2}


def _first_number(segment: str) -> int | None:
    found = []
    for regex, parse in ((_DIGITS_RE, int), (_THAI_NUMBER_RE, parse_thai_number), (_EN_NUMBER_RE, parse_english_number)):
        m = regex.search(segment)
        if m:
            found.append((m.start(), parse(m.group())))
    found = [f for f in found if f[1] is not None]
    return min(found)[1] if found else None


def parse_spoken(text: str, products: list[tuple[str, str]]) -> dict[str, int]:
    """Counts for the products mentioned in `text`; a product said without a number is skipped."""
    fixed = fix_layout(text, [name for _, name in products] + list(UNITS))
    squashed = _squash(fixed)

    candidates = [
        (m.start(), -len(alias), m.end(), sku)
        for sku, name in products
        for alias in _aliases(sku, name)
        for m in re.finditer(re.escape(alias), squashed)
    ]
    chosen: list[tuple[int, int, str]] = []
    for start, _, end, sku in sorted(candidates):  # earliest first, longest name first
        if not chosen or start >= chosen[-1][1]:
            chosen.append((start, end, sku))

    counts: dict[str, int] = {}
    for i, (_, end, sku) in enumerate(chosen):
        next_start = chosen[i + 1][0] if i + 1 < len(chosen) else len(squashed)
        value = _first_number(squashed[end:next_start])
        if value is not None:
            counts[sku] = value
    return counts
