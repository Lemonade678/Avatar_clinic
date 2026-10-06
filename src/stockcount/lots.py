"""Two-year shelf life (ministry rule, every product incl. supplements): which lot runs out of time first?

ณัฑฒ์ chose "A + C" (6/10 round 4):
  A) the date written on the oldest pack, typed in on the lots page — what the shelf really holds;
  C) receiving dates exported from the old stock system — the oldest lot still in stock is estimated
     first-in-first-out (FIFO) from the quantity on hand.
A typed date always wins (a stale one errs on the safe side: an early warning, never a missed one);
the estimate covers every product nobody has typed yet. Pure, apart from reading the export CSV.
"""
from __future__ import annotations

import calendar
import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .thai_digits import parse_count, to_ascii_digits

STATUS_ORDER = ("expired", "soon", "unknown", "ok")  # worst first

# headers seen in Thai and English stock-system exports, matched case- and space-insensitively
RECEIPT_HEADERS = {
    "sku": ("sku", "รหัส", "รหัสสินค้า", "code", "product code", "item code"),
    "date": ("date", "received", "received date", "receive date", "lot date", "วันที่", "วันที่รับ", "วันที่รับสินค้า", "วันรับ"),
    "qty": ("qty", "quantity", "received qty", "จำนวน", "จำนวนรับ"),
}

_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_DMY = re.compile(r"^(\d{1,2})[/.\- ](\d{1,2})[/.\- ](\d{2}|\d{4})$")


class LotError(ValueError):
    pass


@dataclass(frozen=True)
class Receipt:
    sku: str
    received: date
    qty: int


@dataclass(frozen=True)
class ManualLot:
    sku: str
    lot_date: date
    recorded_at: datetime


@dataclass(frozen=True)
class Lot:
    sku: str
    lot_date: date  # the date the warnings count from
    source: str  # "manual" (typed from the pack) or "receipt" (FIFO estimate)
    at_least: bool = False  # receipts do not explain all stock on hand: the oldest lot is even older
    estimate: date | None = None  # the FIFO estimate, kept to compare with a typed date


def _year(text: str) -> int:
    year = int(text)
    if len(text) == 2:  # 60–99 = Buddhist era 2560–2599 (2017–2056); 00–59 = 2000–2059
        return 1957 + year if year >= 60 else 2000 + year
    return year - 543 if year >= 2400 else year


def parse_lot_date(text: str) -> date:
    """17/6/69, 17/06/2569, 17/6/2026, 2026-06-17 (Thai digits too) -> date(2026, 6, 17)."""
    clean = to_ascii_digits(text).strip()
    if m := _ISO.match(clean):
        y, mo, d = m.group(1), m.group(2), m.group(3)
    elif m := _DMY.match(clean):
        d, mo, y = m.group(1), m.group(2), m.group(3)
    else:
        raise LotError(f"cannot read the date '{text}' (expected day/month/year, e.g. 17/6/69)")
    try:
        value = date(_year(y), int(mo), int(d))
    except ValueError as e:
        raise LotError(f"'{text}' is not a real date") from e
    if value.year < 2000:
        raise LotError(f"'{text}' is too old to be a lot date")
    return value


def add_months(d: date, months: int) -> date:
    index = d.year * 12 + d.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def expiry_status(lot_date: date, today: date, shelf_life_months: int = 24, warn_months: int = 3) -> str:
    expires = add_months(lot_date, shelf_life_months)
    if today >= expires:
        return "expired"
    if today >= add_months(expires, -warn_months):
        return "soon"
    return "ok"


def oldest_in_stock(receipts: Iterable[Receipt], on_hand: int) -> tuple[date, bool] | None:
    """FIFO: what is on hand came in last. Returns (oldest lot date, at_least) or None."""
    received = sorted(receipts, key=lambda r: r.received, reverse=True)
    if on_hand <= 0 or not received:
        return None
    left = on_hand
    for r in received:
        left -= r.qty
        if left <= 0:
            return r.received, False
    return received[-1].received, True


def resolve_lots(manual: Iterable[ManualLot], receipts: Iterable[Receipt], on_hand: dict[str, int]) -> dict[str, Lot]:
    """sku -> the lot the shelf-life warnings follow (only products we know something about)."""
    typed: dict[str, ManualLot] = {}
    for m in manual:
        if m.sku not in typed or typed[m.sku].recorded_at <= m.recorded_at:
            typed[m.sku] = m
    by_sku: dict[str, list[Receipt]] = defaultdict(list)
    for r in receipts:
        by_sku[r.sku].append(r)

    lots: dict[str, Lot] = {}
    for sku in sorted(set(typed) | set(by_sku)):
        estimate = oldest_in_stock(by_sku.get(sku, ()), on_hand.get(sku, 0))
        if sku in typed:
            lots[sku] = Lot(sku, typed[sku].lot_date, "manual", estimate=estimate[0] if estimate else None)
        elif estimate:
            lots[sku] = Lot(sku, estimate[0], "receipt", at_least=estimate[1], estimate=estimate[0])
    return lots


def _normalise(header: str) -> str:
    return re.sub(r"\s+", " ", header.replace("﻿", "").strip().lower())


def load_receipts_csv(path: str | Path) -> list[Receipt]:
    """Receiving history from the old stock system; rows of the same product and day are added up."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = {_normalise(h): h for h in reader.fieldnames or []}
        columns = {key: next((headers[h] for h in names if h in headers), None) for key, names in RECEIPT_HEADERS.items()}
        missing = [key for key, col in columns.items() if col is None]
        if missing:
            accepted = "; ".join(f"{key}: {', '.join(names)}" for key, names in RECEIPT_HEADERS.items())
            raise LotError(f"receipts CSV is missing {missing} — accepted headers are {accepted}")

        totals: dict[tuple[str, date], int] = defaultdict(int)
        for line_no, rec in enumerate(reader, start=2):
            sku = (rec[columns["sku"]] or "").strip()
            if not sku:
                continue
            try:
                received = parse_lot_date(rec[columns["date"]] or "")
            except LotError as e:
                raise LotError(f"line {line_no}: {e}") from e
            qty = parse_count(rec[columns["qty"]] or "")
            if not qty:  # None (not a number) or 0
                raise LotError(f"line {line_no}: quantity must be a whole number above 0")
            totals[(sku, received)] += qty
    return [Receipt(sku, day, qty) for (sku, day), qty in totals.items()]
