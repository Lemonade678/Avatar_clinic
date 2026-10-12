from pathlib import Path

import pytest

from stockcount.layout import Placement, load_layout_csv
from stockcount.location import parse_location
from stockcount.minimap import build_minimap, item_status
from stockcount.stock_csv import StockRow, load_stock_csv

ROOT = Path(__file__).parents[1]


def row(sku, front, back=0):
    return StockRow(sku, f"name-{sku}", "cat", back, front, back + front, False)


def place(sku, code):
    return Placement(sku, parse_location(code))


def test_item_status_follows_the_front_qty_rule():
    # > 0 must be checked · 0 = not stocked, skip · < 0 = the system record is wrong
    assert [item_status(q) for q in (3, 0, -9)] == ["check", "empty", "problem"]


def test_wall_cells_are_top_storey_first_and_gaps_are_filled():
    m = build_minimap([place("A", "L0101"), place("B", "L0301")], [row("A", 2), row("B", 0)])
    left = m.walls[0]
    assert left.side == "L"
    assert [c.code for c in left.cells] == ["L0301", "L0201", "L0101"]
    assert left.cells[1].status == "free"


def test_each_shelf_unit_is_its_own_wall():
    # the last two digits of a code name the shelf unit: L0101 and L0102 stand on different units
    m = build_minimap([place("A", "L0101"), place("B", "L0102")], [row("A", 1), row("B", 1)])
    assert [(w.side, w.shelf, [c.code for c in w.cells]) for w in m.walls] == [
        ("L", 1, ["L0101"]),
        ("L", 2, ["L0102"]),
        ("R", 1, []),
    ]


def test_cell_status_is_its_worst_item():
    m = build_minimap([place("A", "R0101"), place("B", "R0101")], [row("A", 0), row("B", -9)])
    right = next(w for w in m.walls if w.side == "R")
    assert right.cells[0].status == "problem"


def test_both_sides_exist_even_when_one_is_empty():
    m = build_minimap([place("A", "L0101")], [row("A", 1)])
    assert [(w.side, len(w.cells)) for w in m.walls] == [("L", 1), ("R", 0)]


def test_unplaced_lists_only_products_to_check():
    m = build_minimap([place("A", "L0101")], [row("A", 1), row("B", 4), row("C", 0)])
    assert [i.sku for i in m.unplaced] == ["B"]
    assert (m.total_products, m.placed, m.to_check) == (3, 1, 2)


def test_layout_sku_missing_from_stock_sheet_is_rejected():
    with pytest.raises(ValueError, match="ZZ"):
        build_minimap([place("ZZ", "L0101")], [row("A", 1)])


def test_repo_data():
    m = build_minimap(
        load_layout_csv(ROOT / "data" / "layout_mbk.csv"),
        load_stock_csv(ROOT / "data" / "stock_2026-09-28.csv"),
    )
    left = m.walls[0]
    assert [c.code for c in left.cells] == ["L0301", "L0201", "L0101"]
    assert len(left.cells[0].items) == 10
    assert (m.total_products, m.placed, m.to_check, len(m.unplaced)) == (105, 27, 59, 40)
    pandora_ii = next(i for w in m.walls for c in w.cells for i in c.items if i.sku == "NA0032")
    assert pandora_ii.status == "problem"
