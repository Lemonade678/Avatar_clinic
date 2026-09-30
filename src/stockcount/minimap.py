"""Build the back-room minimap (the sku directory as a floor plan). Pure: no I/O.

Each wall is drawn as seen from the door: storeys top to bottom, positions left to right.
Status comes from the stock sheet quantity: > 0 must be checked, 0 = not stocked (skip),
< 0 = the system record itself is wrong. Once counted today: "done" (matches) or "diff".
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .layout import Placement
from .stock_csv import StockRow

STATUS_ORDER = ("problem", "diff", "check", "done", "empty", "free")  # worst first
SIDES = ("L", "R")


@dataclass(frozen=True)
class MapItem:
    sku: str
    name: str
    qty: int
    status: str
    counted: int | None = None


@dataclass(frozen=True)
class MapCell:
    code: str
    storey: int
    position: int
    items: tuple[MapItem, ...]
    flagged: bool = False  # the CV cross-check disagreed with today's counts

    @property
    def status(self) -> str:
        if not self.items:
            return "free"
        return min((i.status for i in self.items), key=STATUS_ORDER.index)


@dataclass(frozen=True)
class MapWall:
    side: str
    shelf: int
    rows: tuple[tuple[MapCell, ...], ...]  # top storey first; positions left to right


@dataclass(frozen=True)
class Minimap:
    walls: tuple[MapWall, ...]  # left walls, then right walls
    unplaced: tuple[MapItem, ...]  # products to check that have no location yet
    total_products: int
    placed: int
    to_check: int


def item_status(qty: int) -> str:
    if qty < 0:
        return "problem"
    return "check" if qty > 0 else "empty"


def _wall(side: str, shelf: int, here: list[Placement], item_of) -> MapWall:
    top = max((p.location.storey for p in here), default=0)
    width = max((p.location.position for p in here), default=0)
    rows = []
    for storey in range(top, 0, -1):
        cells = []
        for position in range(1, width + 1):
            items = tuple(
                item_of(p.sku) for p in here if (p.location.storey, p.location.position) == (storey, position)
            )
            cells.append(MapCell(f"{side}{storey:02d}{position:02d}", storey, position, items))
        rows.append(tuple(cells))
    return MapWall(side, shelf, tuple(rows))


def build_minimap(placements: list[Placement], rows: list[StockRow], qty_field: str = "front_qty") -> Minimap:
    by_sku = {r.sku: r for r in rows}
    unknown = [p.sku for p in placements if p.sku not in by_sku]
    if unknown:
        raise ValueError(f"layout has skus that are not in the stock sheet: {unknown}")

    def item_of(sku: str) -> MapItem:
        r = by_sku[sku]
        qty = getattr(r, qty_field)
        return MapItem(r.sku, r.name, qty, item_status(qty))

    walls = []
    for side in SIDES:
        shelves = sorted({p.location.shelf for p in placements if p.location.side == side}) or [1]
        for shelf in shelves:
            here = [p for p in placements if (p.location.side, p.location.shelf) == (side, shelf)]
            walls.append(_wall(side, shelf, here, item_of))

    placed = {p.sku for p in placements}
    items = [item_of(r.sku) for r in rows]
    return Minimap(
        walls=tuple(walls),
        unplaced=tuple(i for i in items if i.status == "check" and i.sku not in placed),
        total_products=len(rows),
        placed=len(placed),
        to_check=sum(1 for i in items if i.status == "check"),
    )


def apply_progress(minimap: Minimap, counted: dict[str, int], flagged: set[str]) -> Minimap:
    """Overlay today's counts: counted items become "done" (matches the system) or "diff"."""

    def item(i: MapItem) -> MapItem:
        if i.sku not in counted:
            return i
        value = counted[i.sku]
        return replace(i, counted=value, status="done" if value == i.qty else "diff")

    walls = tuple(
        replace(
            wall,
            rows=tuple(
                tuple(replace(c, items=tuple(item(i) for i in c.items), flagged=c.code in flagged) for c in row)
                for row in wall.rows
            ),
        )
        for wall in minimap.walls
    )
    return replace(minimap, walls=walls)
