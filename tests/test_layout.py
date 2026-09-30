from collections import Counter
from pathlib import Path

import pytest

from stockcount.layout import LayoutError, load_layout_csv

REPO_LAYOUT = Path(__file__).parents[1] / "data" / "layout_mbk.csv"


def write(tmp_path, text):
    p = tmp_path / "layout.csv"
    p.write_text(text, encoding="utf-8")
    return p


def test_reads_placed_rows_and_skips_blanks(tmp_path):
    p = write(tmp_path, "sku,name,location,shelf\nHB0001,อุระกาวาท,R0101,\nHB0003,กัณฑรา,,\n")
    [placement] = load_layout_csv(p)
    assert placement.sku == "HB0001"
    assert placement.location.code == "R0101"
    assert placement.location.shelf == 1


def test_reads_the_original_sheet_headers(tmp_path):
    # ณัฑฒ์'s own export: "MBK  directory" (two spaces) and "Postion" (= shelf number x)
    p = write(tmp_path, "sku,name,MBK  directory,Postion\nHB0001,x,l0301,2\n")
    [placement] = load_layout_csv(p)
    assert (placement.location.code, placement.location.shelf) == ("L0301", 2)


def test_excel_bom_is_ignored(tmp_path):
    p = write(tmp_path, "﻿sku,location\nHB0001,R0101\n")
    assert load_layout_csv(p)[0].sku == "HB0001"


def test_same_sku_placed_twice_is_rejected(tmp_path):
    p = write(tmp_path, "sku,location\nHB0001,R0101\nHB0001,L0101\n")
    with pytest.raises(LayoutError, match="line 3: sku HB0001 is placed twice"):
        load_layout_csv(p)


def test_bad_code_reports_the_line(tmp_path):
    p = write(tmp_path, "sku,location\nHB0001,R0101\nHB0003,X9\n")
    with pytest.raises(LayoutError, match="line 3"):
        load_layout_csv(p)


def test_missing_location_column_is_rejected(tmp_path):
    p = write(tmp_path, "sku,name\nHB0001,x\n")
    with pytest.raises(LayoutError, match="location"):
        load_layout_csv(p)


def test_repo_layout_file():
    placements = load_layout_csv(REPO_LAYOUT)
    assert len(placements) == 27
    by_code = Counter(p.location.code for p in placements)
    assert by_code["L0301"] == 10
    assert set(by_code) == {"L0101", "L0201", "L0301", "R0101", "R0201", "R0301"}
