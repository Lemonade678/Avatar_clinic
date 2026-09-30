from stockcount.layout import Placement
from stockcount.location import parse_location
from stockcount.minimap import build_minimap
from stockcount.render import render_minimap
from stockcount.stock_csv import StockRow


def page(name="อุระกาวาท"):
    rows = [StockRow("HB0001", name, "สมุนไพร (ผง)", 10, 9, 19, False), StockRow("HB0003", "กัณฑรา", "x", 5, 5, 10, False)]
    m = build_minimap([Placement("HB0001", parse_location("R0101"))], rows)
    return render_minimap(m, branch_label="MBK", as_of="28/09/2026", generated_at="30/09/2026 12:00")


def test_page_is_utf8_and_shows_thai():
    html = page()
    assert '<meta charset="utf-8">' in html
    assert "อุระกาวาท" in html
    assert "R0101" in html


def test_product_names_are_html_escaped():
    # a name pasted from a sheet must never run as code in the page
    html = page(name='<script>alert("x")</script>')
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html


def test_unplaced_products_are_listed():
    assert "กัณฑรา" in page()


def test_keyboard_tables_are_embedded_for_search():
    html = page()
    assert "const EN_TO_TH" in html and "const TH_TO_EN" in html
