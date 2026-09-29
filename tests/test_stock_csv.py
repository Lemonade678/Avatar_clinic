from pathlib import Path

import pytest

from stockcount.stock_csv import StockCsvError, load_stock_csv

HEADER = "sku,name,category,back_qty,front_qty,system_qty,needs_review\n"
REPO_CSV = Path(__file__).parents[1] / "data" / "stock_2026-09-28.csv"


def write(tmp_path, body, bom=False):
    p = tmp_path / "s.csv"
    p.write_text(("﻿" if bom else "") + HEADER + body, encoding="utf-8")
    return p


def test_reads_typed_row(tmp_path):
    [row] = load_stock_csv(write(tmp_path, "HB0001,อุระกาวาท,สมุนไพร (ผง),10,9,19,false\n"))
    assert (row.sku, row.name, row.back_qty, row.front_qty, row.system_qty) == ("HB0001", "อุระกาวาท", 10, 9, 19)
    assert row.needs_review is False


def test_excel_bom_is_ignored(tmp_path):
    [row] = load_stock_csv(write(tmp_path, "HB0001,x,y,1,2,3,false\n", bom=True))
    assert row.sku == "HB0001"


def test_negative_front_quantity_is_kept(tmp_path):
    [row] = load_stock_csv(write(tmp_path, "X1,x,y,30,-9,21,true\n"))
    assert row.front_qty == -9
    assert row.needs_review is True


def test_duplicate_sku_is_rejected(tmp_path):
    with pytest.raises(StockCsvError, match="duplicate sku X1"):
        load_stock_csv(write(tmp_path, "X1,a,c,1,1,2,false\nX1,b,c,1,1,2,false\n"))


def test_non_integer_quantity_is_rejected(tmp_path):
    with pytest.raises(StockCsvError, match="line 2"):
        load_stock_csv(write(tmp_path, "X1,a,c,1.5,1,2,false\n"))


def test_system_qty_must_equal_back_plus_front(tmp_path):
    # catches transcription slips: the sheet's คงเหลือ is always หลังร้าน + หน้าร้าน
    with pytest.raises(StockCsvError, match=r"line 2: system_qty 5 != back_qty 1 \+ front_qty 1"):
        load_stock_csv(write(tmp_path, "X1,a,c,1,1,5,false\n"))


def test_missing_column_is_rejected(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("sku,name\nX1,a\n", encoding="utf-8")
    with pytest.raises(StockCsvError, match="missing columns"):
        load_stock_csv(p)


def test_repo_sheet_has_105_real_codes():
    rows = load_stock_csv(REPO_CSV)
    assert len(rows) == 105
    assert all(r.sku[:2] in {"NA", "HB", "BK"} and len(r.sku) == 6 for r in rows)
    pandora_ii = next(r for r in rows if r.sku == "NA0032")
    assert (pandora_ii.back_qty, pandora_ii.front_qty, pandora_ii.system_qty) == (30, -9, 21)
