from datetime import date, datetime, timezone

import pytest

from stockcount.lots import (
    Lot,
    LotError,
    ManualLot,
    Receipt,
    add_months,
    expiry_status,
    load_receipts_csv,
    oldest_in_stock,
    parse_lot_date,
    resolve_lots,
)

UTC = timezone.utc


# --- dates as people write them on the packs ------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["17/6/69", "17/06/2569", "17/6/2026", "2026-06-17", "17-6-69", "17.6.69", " 17/6/69 ", "๑๗/๖/๖๙"],
)
def test_lot_dates_are_read_the_way_they_are_written(text):
    # Buddhist-era short years (69 = 2569 = 2026) are what ณัฑฒ์ writes on the bags
    assert parse_lot_date(text) == date(2026, 6, 17)


def test_two_digit_years_below_60_are_christian_era():
    assert parse_lot_date("17/6/26") == date(2026, 6, 17)


@pytest.mark.parametrize("text", ["", "abc", "31/2/69", "17/13/69", "17/6", "1/1/1999"])
def test_unreadable_or_impossible_dates_are_refused(text):
    with pytest.raises(LotError):
        parse_lot_date(text)


# --- the two-year clock ----------------------------------------------------------------------------
def test_add_months_keeps_the_day_or_falls_back_to_month_end():
    assert add_months(date(2026, 6, 17), 24) == date(2028, 6, 17)
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 2, 29), 24) == date(2026, 2, 28)
    assert add_months(date(2026, 6, 17), -3) == date(2026, 3, 17)


@pytest.mark.parametrize(
    "today, status",
    [
        (date(2026, 3, 16), "ok"),
        (date(2026, 3, 17), "soon"),  # 3 months before the 2 years are up
        (date(2026, 6, 16), "soon"),
        (date(2026, 6, 17), "expired"),
    ],
)
def test_expiry_status_warns_three_months_ahead(today, status):
    assert expiry_status(date(2024, 6, 17), today, shelf_life_months=24, warn_months=3) == status


# --- C: receiving dates -> the oldest lot still in stock (first in, first out) ---------------------
RECEIPTS = [
    Receipt("A", date(2026, 1, 10), 10),
    Receipt("A", date(2026, 5, 1), 5),
    Receipt("A", date(2026, 3, 1), 5),
]


def test_stock_on_hand_is_the_newest_receipts():
    assert oldest_in_stock(RECEIPTS, on_hand=5) == (date(2026, 5, 1), False)
    assert oldest_in_stock(RECEIPTS, on_hand=8) == (date(2026, 3, 1), False)
    assert oldest_in_stock(RECEIPTS, on_hand=20) == (date(2026, 1, 10), False)


def test_more_stock_than_receipts_means_at_least_as_old_as_the_oldest_receipt():
    assert oldest_in_stock(RECEIPTS, on_hand=21) == (date(2026, 1, 10), True)


def test_no_stock_or_no_receipts_gives_no_lot():
    assert oldest_in_stock(RECEIPTS, on_hand=0) is None
    assert oldest_in_stock([], on_hand=5) is None


# --- A + C together --------------------------------------------------------------------------------
def test_a_typed_date_wins_and_the_estimate_is_kept_for_comparison():
    manual = [
        ManualLot("A", date(2025, 12, 1), datetime(2026, 9, 1, tzinfo=UTC)),
        ManualLot("A", date(2026, 2, 1), datetime(2026, 10, 1, tzinfo=UTC)),  # newest entry wins
    ]
    lots = resolve_lots(manual, RECEIPTS, {"A": 8})
    assert lots["A"] == Lot("A", date(2026, 2, 1), "manual", estimate=date(2026, 3, 1))


def test_products_without_a_typed_date_use_the_estimate():
    lots = resolve_lots([], RECEIPTS + [Receipt("B", date(2026, 4, 4), 3)], {"A": 21, "B": 2})
    assert lots["A"] == Lot("A", date(2026, 1, 10), "receipt", at_least=True, estimate=date(2026, 1, 10))
    assert lots["B"] == Lot("B", date(2026, 4, 4), "receipt", estimate=date(2026, 4, 4))


def test_products_with_nothing_known_are_left_out():
    assert resolve_lots([], RECEIPTS, {"A": 5, "Z": 4}).keys() == {"A"}


# --- the old stock system's export ------------------------------------------------------------------
def write(tmp_path, text):
    p = tmp_path / "receipts.csv"
    p.write_text(text, encoding="utf-8")
    return p


def test_receipts_csv_reads_thai_headers_and_merges_same_day_rows(tmp_path):
    p = write(tmp_path, "﻿รหัสสินค้า,ชื่อ,วันที่รับ,จำนวน\nHB0001,x,17/6/69,4\nHB0001,x,17/6/69,๒\nHB0004,y,2026-07-01,3\n")
    assert load_receipts_csv(p) == [
        Receipt("HB0001", date(2026, 6, 17), 6),
        Receipt("HB0004", date(2026, 7, 1), 3),
    ]


def test_receipts_csv_reads_english_headers(tmp_path):
    p = write(tmp_path, "SKU,Received Date,Qty\nHB0001,17/06/2026,4\n")
    assert load_receipts_csv(p) == [Receipt("HB0001", date(2026, 6, 17), 4)]


def test_receipts_csv_names_the_bad_line(tmp_path):
    p = write(tmp_path, "sku,date,qty\nHB0001,17/6/69,4\nHB0004,31/2/69,3\n")
    with pytest.raises(LotError, match="line 3"):
        load_receipts_csv(p)


def test_receipts_csv_refuses_zero_or_negative_quantities(tmp_path):
    p = write(tmp_path, "sku,date,qty\nHB0001,17/6/69,0\n")
    with pytest.raises(LotError, match="line 2"):
        load_receipts_csv(p)


def test_receipts_csv_without_the_needed_columns_says_which_headers_work(tmp_path):
    p = write(tmp_path, "code,when\nHB0001,17/6/69\n")
    with pytest.raises(LotError, match="วันที่รับ"):
        load_receipts_csv(p)
