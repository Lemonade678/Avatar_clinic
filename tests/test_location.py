import pytest

from stockcount.location import LocationError, parse_location


def test_parses_side_storey_position():
    loc = parse_location("L0301")
    assert (loc.side, loc.storey, loc.position, loc.shelf) == ("L", 3, 1, 1)
    assert loc.code == "L0301"


def test_lowercase_and_spaces_are_accepted():
    assert parse_location(" r0102 ").code == "R0102"


def test_shelf_number_is_kept():
    assert parse_location("R0201", shelf=2).shelf == 2


@pytest.mark.parametrize("bad", ["", "X0101", "L301", "L00101", "L0001", "L0100", "L01A1"])
def test_bad_codes_are_rejected(bad):
    with pytest.raises(LocationError):
        parse_location(bad)


def test_shelf_number_must_be_positive():
    with pytest.raises(LocationError):
        parse_location("L0101", shelf=0)
