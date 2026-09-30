"""Load a stock sheet + the slot layout into Supabase.

Usage: .venv/Scripts/python scripts/import_csv.py data/stock_2026-09-28.csv 2026-09-28
The layout file comes from config.yaml -> layout_file. Run it again whenever the layout changes.
"""
import os
import sys
from datetime import date

from dotenv import load_dotenv
from supabase import create_client

from stockcount.config import load_config
from stockcount.layout import load_layout_csv, load_packaging_csv
from stockcount.seed import build_seed
from stockcount.stock_csv import load_stock_csv


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        sys.exit(__doc__)
    load_dotenv()
    cfg = load_config("config.yaml")
    seed = build_seed(
        load_stock_csv(argv[1]),
        load_layout_csv(cfg.layout_file),
        load_packaging_csv(cfg.layout_file),
        date.fromisoformat(argv[2]),
        cfg.cv,
    )
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    db.table("products").upsert(seed.products, on_conflict="sku").execute()
    if seed.locations:
        db.table("locations").upsert(seed.locations, on_conflict="code").execute()
    # the layout file is the whole truth: replace, don't merge
    db.table("product_locations").delete().neq("sku", "").execute()
    if seed.product_locations:
        db.table("product_locations").insert(seed.product_locations).execute()
    db.table("stock_snapshots").upsert(seed.snapshots, on_conflict="sku,as_of").execute()

    print(
        f"products={len(seed.products)} locations={len(seed.locations)} "
        f"product_locations={len(seed.product_locations)} snapshots={len(seed.snapshots)}"
    )


if __name__ == "__main__":
    main(sys.argv)
