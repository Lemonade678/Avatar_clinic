"""Turn config + stock rows into the rows the database seed needs. Pure: no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import AppConfig
from .stock_csv import StockRow


class SeedError(ValueError):
    pass


@dataclass(frozen=True)
class SeedData:
    products: list[dict]
    shelves: list[dict]
    shelf_products: list[dict]
    snapshots: list[dict]


def build_seed(config: AppConfig, rows: list[StockRow], as_of: date) -> SeedData:
    known = {r.sku for r in rows}
    missing = sorted(sku for shelf in config.shelves.values() for sku in shelf.skus if sku not in known)
    if missing:
        raise SeedError(f"skus in config.yaml but not in CSV: {missing}")

    return SeedData(
        products=[{"sku": r.sku, "name": r.name, "category": r.category} for r in rows],
        shelves=[{"code": s.code, "label": s.label} for s in config.shelves.values()],
        shelf_products=[
            {"shelf_code": s.code, "sku": sku, "position": i}
            for s in config.shelves.values()
            for i, sku in enumerate(s.skus, start=1)
        ],
        snapshots=[{"sku": r.sku, "back_qty": r.back_qty, "as_of": as_of.isoformat()} for r in rows],
    )
