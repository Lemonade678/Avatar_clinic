"""Load receiving dates exported from the old stock system (method C of the two-year shelf life).

Usage: .venv/Scripts/python scripts/import_lots.py <export.csv>
The CSV needs a product code, a receiving date and a quantity; Thai or English headers both work
(see RECEIPT_HEADERS in src/stockcount/lots.py). Each run replaces the previous import, dates typed on
the lots page stay. Codes missing from the products table are listed and skipped.
"""
import sys

from dotenv import load_dotenv

from stockcount.lots import LotError, load_receipts_csv
from stockcount.repo import SupabaseRepo


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        sys.exit(__doc__)
    load_dotenv()
    try:
        receipts = load_receipts_csv(argv[1])
    except (LotError, OSError) as e:
        sys.exit(f"cannot import {argv[1]}: {e}")
    repo = SupabaseRepo.from_env()
    known = set(repo.products())
    kept = [r for r in receipts if r.sku in known]
    unknown = sorted({r.sku for r in receipts} - known)
    repo.replace_receipts(kept)
    print(f"receipts={len(kept)} products={len({r.sku for r in kept})}")
    if unknown:
        print(f"skipped {len(unknown)} codes that are not in the products table: {', '.join(unknown)}")


if __name__ == "__main__":
    main(sys.argv)
