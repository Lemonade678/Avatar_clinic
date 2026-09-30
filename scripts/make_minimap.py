"""Write the back-room minimap as one standalone HTML page (no internet needed, nothing is uploaded).

Usage: .venv/Scripts/python scripts/make_minimap.py data/layout_mbk.csv data/stock_2026-09-28.csv
Output: out/minimap_<branch>.html
"""
import re
import sys
from datetime import datetime
from pathlib import Path

from stockcount.config import load_config
from stockcount.layout import load_layout_csv
from stockcount.minimap import build_minimap
from stockcount.render import render_minimap
from stockcount.stock_csv import load_stock_csv


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        sys.exit(__doc__)
    layout_path, stock_path = argv[1], argv[2]
    cfg = load_config("config.yaml")
    minimap = build_minimap(load_layout_csv(layout_path), load_stock_csv(stock_path))

    found = re.search(r"(\d{4})-(\d{2})-(\d{2})", Path(stock_path).name)
    as_of = f"{found.group(3)}/{found.group(2)}/{found.group(1)}" if found else Path(stock_path).name

    out = Path("out") / f"minimap_{cfg.branch}.html"
    out.parent.mkdir(exist_ok=True)
    html = render_minimap(
        minimap,
        branch_label=cfg.branch.upper(),
        as_of=as_of,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} · placed {minimap.placed}/{minimap.total_products} · to check {minimap.to_check} · unplaced {len(minimap.unplaced)}")


if __name__ == "__main__":
    main(sys.argv)
