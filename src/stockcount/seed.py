"""Turn the stock sheet + layout into the rows the database needs. Pure: no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import CvConfig
from .layout import Placement
from .stock_csv import StockRow


class SeedError(ValueError):
    pass


@dataclass(frozen=True)
class SeedData:
    products: list[dict]
    locations: list[dict]
    product_locations: list[dict]
    snapshots: list[dict]


def build_seed(
    rows: list[StockRow],
    placements: list[Placement],
    packaging: dict[str, str],
    as_of: date,
    cv: CvConfig,
) -> SeedData:
    known = {r.sku for r in rows}
    missing = sorted({p.sku for p in placements} - known)
    if missing:
        raise SeedError(f"skus in the layout but not in the stock sheet: {missing}")
    ghosts = sorted(set(packaging) - known)
    if ghosts:
        raise SeedError(f"packaging given for skus not in the stock sheet: {ghosts}")

    locations: dict[str, dict] = {}
    for p in placements:
        loc = p.location
        locations.setdefault(
            loc.code,
            {
                "code": loc.code,
                "side": loc.side,
                "storey": loc.storey,
                "position": loc.position,
                "shelf": loc.shelf,
                "cv_enabled": cv.is_enabled_for(loc.code),
            },
        )

    return SeedData(
        products=[
            {"sku": r.sku, "name": r.name, "category": r.category, "packaging": packaging.get(r.sku)} for r in rows
        ],
        locations=sorted(locations.values(), key=lambda d: (d["side"], d["shelf"], d["storey"], d["position"])),
        product_locations=[{"sku": p.sku, "location_code": p.location.code} for p in placements],
        snapshots=[
            {"sku": r.sku, "back_qty": r.back_qty, "front_qty": r.front_qty, "as_of": as_of.isoformat()} for r in rows
        ],
    )
