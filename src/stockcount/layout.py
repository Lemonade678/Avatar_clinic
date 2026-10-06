"""Load where each product sits (the sku directory) from a CSV."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .location import Location, parse_location

# headers are matched loosely so ณัฑฒ์'s own sheet export ("MBK  directory", "Postion") also loads
LOCATION_HEADERS = {"location", "mbk directory", "directory"}
SHELF_HEADERS = {"shelf", "postion"}
# what the small CV model can see on a shelf (ณัฑฒ์, 6/10): paper medicine bag, plastic medicine bag,
# plastic bottle, box, tote bag, inhaler tin — a product with no class is simply not cross-checked
PACKAGING = ("paper_bag", "plastic_bag", "plastic_bottle", "box", "tote_bag", "tin")


class LayoutError(ValueError):
    pass


@dataclass(frozen=True)
class Placement:
    sku: str
    location: Location


def _normalise(header: str) -> str:
    return re.sub(r"\s+", " ", header.strip().lower())


def load_layout_csv(path: str | Path) -> list[Placement]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = {_normalise(h): h for h in reader.fieldnames or []}
        sku_col = headers.get("sku")
        loc_col = next((headers[h] for h in headers if h in LOCATION_HEADERS), None)
        shelf_col = next((headers[h] for h in headers if h in SHELF_HEADERS), None)
        if not sku_col or not loc_col:
            raise LayoutError("layout CSV needs a 'sku' column and a 'location' column")

        placements: list[Placement] = []
        seen: set[str] = set()
        for line_no, rec in enumerate(reader, start=2):
            code = (rec[loc_col] or "").strip()
            if not code:
                continue  # not placed yet
            sku = rec[sku_col].strip()
            if sku in seen:
                raise LayoutError(f"line {line_no}: sku {sku} is placed twice")
            seen.add(sku)
            shelf_raw = (rec[shelf_col] or "").strip() if shelf_col else ""
            try:
                placements.append(Placement(sku, parse_location(code, int(shelf_raw) if shelf_raw else 1)))
            except ValueError as e:  # LocationError is a ValueError too
                raise LayoutError(f"line {line_no}: {e}") from e
    return placements


def load_packaging_csv(path: str | Path) -> dict[str, str]:
    """sku -> packaging class, for every row that has one (placed or not)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = {_normalise(h): h for h in reader.fieldnames or []}
        sku_col, pack_col = headers.get("sku"), headers.get("packaging")
        if not sku_col:
            raise LayoutError("layout CSV needs a 'sku' column")
        if not pack_col:
            return {}
        packaging: dict[str, str] = {}
        for line_no, rec in enumerate(reader, start=2):
            value = (rec[pack_col] or "").strip().lower()
            if not value:
                continue
            if value not in PACKAGING:
                raise LayoutError(f"line {line_no}: packaging '{value}' is not one of {PACKAGING}")
            packaging[rec[sku_col].strip()] = value
    return packaging
