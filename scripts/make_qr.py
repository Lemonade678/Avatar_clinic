"""Write printable QR labels: one PNG per slot + A4 pages (PNG and one PDF) with cut lines.

Usage (PowerShell or Git Bash):
  .venv/Scripts/python scripts/make_qr.py                      # uses liff_id from config.yaml
  .venv/Scripts/python scripts/make_qr.py https://your-app.up.railway.app   # before LIFF exists
Output: out/qr/
"""
import sys
from pathlib import Path

from stockcount.config import load_config
from stockcount.layout import load_layout_csv
from stockcount.qr import render_label, render_sheet, slot_url


def main(argv: list[str]) -> None:
    base_url = argv[1] if len(argv) > 1 else ""
    cfg = load_config("config.yaml")
    locations = {p.location.code: p.location for p in load_layout_csv(cfg.layout_file)}
    codes = [l.code for l in sorted(locations.values(), key=lambda l: (l.side, l.shelf, -l.storey, l.position))]
    try:
        urls = {code: slot_url(code, cfg.liff_id, base_url) for code in codes}
    except ValueError as e:
        sys.exit(str(e))

    out = Path("out/qr")
    out.mkdir(parents=True, exist_ok=True)
    labels = []
    for code in codes:
        label = render_label(code, urls[code])
        label.save(out / f"slot-{code}.png")
        labels.append(label)
    pages = render_sheet(labels)
    for n, page in enumerate(pages, start=1):
        page.save(out / f"sheet-A4-{n}.png")
    pages[0].save(out / "labels-A4.pdf", save_all=True, append_images=pages[1:], resolution=150)
    print(f"wrote {len(codes)} labels + {len(pages)} A4 page(s) to {out} · first link: {urls[codes[0]]}")


if __name__ == "__main__":
    main(sys.argv)
