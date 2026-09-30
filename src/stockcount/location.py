"""Shelf location codes from the sku directory: <side><storey:02><position:02>.

L0301 = left wall, storey (z) 3, position (y) 1. The shelf-unit number (x) lives in its
own column because MBK has a single shelf unit per side, so it is almost always 1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

LOCATION_RE = re.compile(r"^([LR])(\d{2})(\d{2})$")


class LocationError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class Location:
    side: str  # "L" or "R", as seen from the door
    storey: int  # z: shelf level
    position: int  # y: slot along the shelf
    shelf: int = 1  # x: shelf unit on that side

    @property
    def code(self) -> str:
        return f"{self.side}{self.storey:02d}{self.position:02d}"


def parse_location(code: str, shelf: int = 1) -> Location:
    m = LOCATION_RE.match(code.strip().upper())
    if not m:
        raise LocationError(f"bad location code '{code}' (expected e.g. L0301: side L/R + 2-digit storey + 2-digit position)")
    side, storey, position = m.group(1), int(m.group(2)), int(m.group(3))
    if storey < 1 or position < 1:
        raise LocationError(f"bad location code '{code}': storey and position start at 01")
    if shelf < 1:
        raise LocationError(f"bad shelf number {shelf} for '{code}': shelves start at 1")
    return Location(side=side, storey=storey, position=position, shelf=shelf)
