from datetime import date
from pathlib import Path

import pytest

from stockcount.config import load_config, parse_config
from stockcount.seed import SeedError, build_seed
from stockcount.stock_csv import StockRow, load_stock_csv

ROOT = Path(__file__).parents[1]


def row(sku, back=0):
    return StockRow(sku, f"name-{sku}", "cat", back, 0, back, False)


def test_builds_rows_for_every_table():
    cfg = parse_config({"branch": "b", "line_basic_id": "@x", "shelves": {"A1": {"label": "L", "skus": ["S2", "S1"]}}})
    seed = build_seed(cfg, [row("S1", 3), row("S2", 4)], date(2026, 9, 28))
    assert seed.products == [
        {"sku": "S1", "name": "name-S1", "category": "cat"},
        {"sku": "S2", "name": "name-S2", "category": "cat"},
    ]
    assert seed.shelves == [{"code": "A1", "label": "L"}]
    assert seed.shelf_products == [
        {"shelf_code": "A1", "sku": "S2", "position": 1},
        {"shelf_code": "A1", "sku": "S1", "position": 2},
    ]
    assert {"sku": "S1", "back_qty": 3, "as_of": "2026-09-28"} in seed.snapshots


def test_config_sku_missing_from_csv_is_rejected():
    cfg = parse_config({"branch": "b", "line_basic_id": "@x", "shelves": {"A1": {"skus": ["NOPE"]}}})
    with pytest.raises(SeedError, match="NOPE"):
        build_seed(cfg, [row("S1")], date(2026, 9, 28))


def test_repo_config_matches_repo_csv():
    seed = build_seed(
        load_config(ROOT / "config.yaml"),
        load_stock_csv(ROOT / "data" / "stock_2026-09-28.csv"),
        date(2026, 9, 28),
    )
    assert len(seed.products) == 105
    assert {"shelf_code": "A1", "sku": "HB0001", "position": 1} in seed.shelf_products
