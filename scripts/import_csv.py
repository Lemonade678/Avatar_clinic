"""Load the stock CSV + config.yaml layout into Supabase.

Usage: .venv/Scripts/python scripts/import_csv.py data/stock_2026-09-28.csv 2026-09-28
"""
import os
import sys
from datetime import date

from dotenv import load_dotenv
from supabase import create_client

from stockcount.config import load_config
from stockcount.seed import build_seed
from stockcount.stock_csv import load_stock_csv


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        sys.exit(__doc__)
    load_dotenv()
    seed = build_seed(load_config("config.yaml"), load_stock_csv(argv[1]), date.fromisoformat(argv[2]))
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    db.table("products").upsert(seed.products, on_conflict="sku").execute()
    db.table("shelves").upsert(seed.shelves, on_conflict="code").execute()
    # the layout in config.yaml is the whole truth: replace, don't merge
    db.table("shelf_products").delete().neq("shelf_code", "").execute()
    db.table("shelf_products").insert(seed.shelf_products).execute()
    db.table("stock_snapshots").upsert(seed.snapshots, on_conflict="sku,as_of").execute()

    print(
        f"products={len(seed.products)} shelves={len(seed.shelves)} "
        f"shelf_products={len(seed.shelf_products)} snapshots={len(seed.snapshots)}"
    )


if __name__ == "__main__":
    main(sys.argv)
