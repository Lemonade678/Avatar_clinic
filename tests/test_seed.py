from datetime import date
from pathlib import Path

import pytest

from stockcount.config import CvConfig
from stockcount.layout import Placement, load_layout_csv, load_packaging_csv
from stockcount.location import parse_location
from stockcount.seed import SeedError, build_seed
from stockcount.stock_csv import StockRow, load_stock_csv

ROOT = Path(__file__).parents[1]
DAY = date(2026, 9, 28)


def row(sku, back=0, front=0):
    return StockRow(sku, f"name-{sku}", "cat", back, front, back + front, False)


def place(sku, code, shelf=1):
    return Placement(sku, parse_location(code, shelf))


def test_builds_rows_for_every_table():
    seed = build_seed(
        [row("S1", 3, 4), row("S2")],
        [place("S1", "L0301"), place("S2", "L0301")],
        {"S1": "bottle"},
        DAY,
        CvConfig(disabled_locations=frozenset({"L0301"})),
    )
    assert seed.products == [
        {"sku": "S1", "name": "name-S1", "category": "cat", "packaging": "bottle"},
        {"sku": "S2", "name": "name-S2", "category": "cat", "packaging": None},
    ]
    assert seed.locations == [
        {"code": "L0301", "side": "L", "storey": 3, "position": 1, "shelf": 1, "cv_enabled": False}
    ]
    assert seed.product_locations == [
        {"sku": "S1", "location_code": "L0301"},
        {"sku": "S2", "location_code": "L0301"},
    ]
    assert {"sku": "S1", "back_qty": 3, "front_qty": 4, "as_of": "2026-09-28"} in seed.snapshots


def test_placed_sku_missing_from_stock_sheet_is_rejected():
    with pytest.raises(SeedError, match="NOPE"):
        build_seed([row("S1")], [place("NOPE", "L0101")], {}, DAY, CvConfig())


def test_packaging_for_unknown_sku_is_rejected():
    with pytest.raises(SeedError, match="GHOST"):
        build_seed([row("S1")], [], {"GHOST": "box"}, DAY, CvConfig())


def test_repo_data_seeds_cleanly():
    layout = ROOT / "data" / "layout_mbk.csv"
    seed = build_seed(
        load_stock_csv(ROOT / "data" / "stock_2026-09-28.csv"),
        load_layout_csv(layout),
        load_packaging_csv(layout),
        DAY,
        CvConfig(),
    )
    assert len(seed.products) == 105
    assert len(seed.locations) == 6
    assert len(seed.product_locations) == 27
