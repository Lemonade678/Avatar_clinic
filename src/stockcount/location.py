"""Shelf location codes from the sku directory: <side><storey:02><shelf:02>.

L0301 = left wall (as seen from the door), storey 3 counted from the floor, shelf unit 01.
ณัฑฒ์ 6/10 (round 4): the last two digits name the shelf unit — MBK has one per side, so it is always 01 there.
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
    storey: int  # shelf level, 1 = bottom
    shelf: int  # shelf unit on that side

    @property
    def code(self) -> str:
        return f"{self.side}{self.storey:02d}{self.shelf:02d}"


def parse_location(code: str) -> Location:
    m = LOCATION_RE.match(code.strip().upper())
    if not m:
        raise LocationError(f"bad location code '{code}' (expected e.g. L0301: side L/R + 2-digit storey + 2-digit shelf)")
    side, storey, shelf = m.group(1), int(m.group(2)), int(m.group(3))
    if storey < 1 or shelf < 1:
        raise LocationError(f"bad location code '{code}': storey and shelf start at 01")
    return Location(side=side, storey=storey, shelf=shelf)
