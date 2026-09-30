"""Printable QR labels, one per slot. Scanning a label opens that slot inside LINE (LIFF)."""
from __future__ import annotations

from urllib.parse import quote

import qrcode
from PIL import Image, ImageDraw, ImageFont

A4_PX = (1240, 1754)  # A4 at 150 dpi
PER_PAGE = (2, 3)  # columns x rows
TEXT_BAND = 150


def slot_url(code: str, liff_id: str = "", base_url: str = "") -> str:
    if liff_id and liff_id != "CHANGE-ME":
        return f"https://liff.line.me/{quote(liff_id, safe='')}?loc={code}"
    if base_url:
        return f"{base_url.rstrip('/')}/loc/{code}"
    raise ValueError("set liff_id in config.yaml (or pass a base URL) before printing labels")


def render_label(code: str, url: str, box_size: int = 12) -> Image.Image:
    # high error correction: a label that gets scratched or photographed at an angle still reads
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=box_size, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    code_img = qr.make_image().get_image().convert("RGB")
    width, height = code_img.size
    label = Image.new("RGB", (width, height + TEXT_BAND), "white")
    label.paste(code_img, (0, 0))
    draw = ImageDraw.Draw(label)
    # slot codes are A-Z/0-9, so Pillow's built-in font is enough (no Thai glyphs needed)
    draw.text((width // 2, height + TEXT_BAND // 2 - 10), code, fill="black", font=ImageFont.load_default(size=96), anchor="mm")
    draw.text((width // 2, height + TEXT_BAND - 22), "STOCK COUNT", fill="#666666", font=ImageFont.load_default(size=26), anchor="mm")
    return label


def render_sheet(labels: list[Image.Image]) -> list[Image.Image]:
    """Lay labels out on A4 pages, 6 per page, each scaled to fit its cell."""
    cols, rows = PER_PAGE
    cell_w, cell_h = A4_PX[0] // cols, A4_PX[1] // rows
    pages = []
    for start in range(0, len(labels), cols * rows):
        page = Image.new("RGB", A4_PX, "white")
        draw = ImageDraw.Draw(page)
        for i, label in enumerate(labels[start:start + cols * rows]):
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            fitted = label.copy()
            fitted.thumbnail((cell_w - 60, cell_h - 60))
            page.paste(fitted, (x + (cell_w - fitted.width) // 2, y + (cell_h - fitted.height) // 2))
            draw.rectangle([x + 10, y + 10, x + cell_w - 10, y + cell_h - 10], outline="#cccccc", width=2)  # cut line
        pages.append(page)
    return pages
