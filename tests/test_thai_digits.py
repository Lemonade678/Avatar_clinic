import pytest

from stockcount.thai_digits import parse_count, to_ascii_digits


def test_thai_digits_become_ascii():
    assert to_ascii_digits("๑๒ ขวด") == "12 ขวด"


@pytest.mark.parametrize("raw, value", [("7", 7), (" 12 ", 12), ("๙", 9), ("0", 0)])
def test_valid_counts(raw, value):
    assert parse_count(raw) == value


@pytest.mark.parametrize("raw", ["", "  ", "-3", "1.5", "7 8", "abc", "๑a"])
def test_invalid_counts(raw):
    assert parse_count(raw) is None
