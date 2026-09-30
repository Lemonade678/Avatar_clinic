import re

import pytest

from stockcount.qr import A4_PX, render_label, render_sheet, slot_url

# the same pattern static/scan.js uses to find the slot inside a scanned QR
SCAN_RE = re.compile(r"(?:loc[=/])?\b([LR]\d{4})\b", re.I)


def test_liff_link_opens_the_slot_inside_line():
    url = slot_url("L0301", liff_id="2001234567-AbCdEfGh")
    assert url == "https://liff.line.me/2001234567-AbCdEfGh?loc=L0301"
    assert SCAN_RE.search(url).group(1) == "L0301"


def test_plain_link_when_there_is_no_liff_yet():
    url = slot_url("R0101", base_url="https://stock.example.app/")
    assert url == "https://stock.example.app/loc/R0101"
    assert SCAN_RE.search(url).group(1) == "R0101"


def test_placeholder_liff_id_is_not_used():
    with pytest.raises(ValueError, match="liff_id"):
        slot_url("L0101", liff_id="CHANGE-ME")


def test_label_has_room_for_the_code_under_the_qr():
    img = render_label("L0301", slot_url("L0301", base_url="https://x.app"))
    width, height = img.size
    assert height > width


def test_sheet_is_a4_and_fits_many_labels():
    labels = [render_label(c, slot_url(c, base_url="https://x.app")) for c in ("L0101", "L0201", "L0301", "R0101", "R0201", "R0301", "R0401")]
    pages = render_sheet(labels)
    assert len(pages) == 2  # 6 labels per A4 page
    assert all(p.size == A4_PX for p in pages)
