"""Read the transcribed stock sheet CSV into typed rows."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = ("sku", "name", "category", "back_qty", "front_qty", "system_qty", "needs_review")
QTY_COLUMNS = ("back_qty", "front_qty", "system_qty")


class StockCsvError(ValueError):
    pass


@dataclass(frozen=True)
class StockRow:
    sku: str
    name: str
    category: str
    back_qty: int
    front_qty: int
    system_qty: int
    needs_review: bool


def load_stock_csv(path: str | Path) -> list[StockRow]:
    # utf-8-sig strips the BOM Excel adds when it re-saves the file
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise StockCsvError(f"missing columns: {missing}")

        rows: list[StockRow] = []
        seen: set[str] = set()
        for line_no, rec in enumerate(reader, start=2):
            sku = rec["sku"].strip()
            if not sku:
                raise StockCsvError(f"line {line_no}: empty sku")
            if sku in seen:
                raise StockCsvError(f"line {line_no}: duplicate sku {sku}")
            seen.add(sku)
            try:
                back, front, system = (int(rec[c]) for c in QTY_COLUMNS)
            except ValueError as e:
                raise StockCsvError(f"line {line_no}: quantity is not a whole number") from e
            if system != back + front:
                raise StockCsvError(f"line {line_no}: system_qty {system} != back_qty {back} + front_qty {front}")
            rows.append(
                StockRow(
                    sku=sku,
                    name=rec["name"].strip(),
                    category=rec["category"].strip(),
                    back_qty=back,
                    front_qty=front,
                    system_qty=system,
                    needs_review=rec["needs_review"].strip().lower() == "true",
                )
            )
    return rows
