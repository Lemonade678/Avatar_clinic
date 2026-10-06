import pytest

from stockcount.location import LocationError, parse_location


def test_parses_side_storey_shelf():
    # ณัฑฒ์ 6/10 (round 4): the last two digits name the shelf unit — MBK has one, "01"
    loc = parse_location("L0301")
    assert (loc.side, loc.storey, loc.shelf) == ("L", 3, 1)
    assert loc.code == "L0301"


def test_a_second_shelf_unit_is_read_from_the_code():
    loc = parse_location("R0202")
    assert (loc.side, loc.storey, loc.shelf) == ("R", 2, 2)


def test_lowercase_and_spaces_are_accepted():
    assert parse_location(" r0102 ").code == "R0102"


@pytest.mark.parametrize("bad", ["", "X0101", "L301", "L00101", "L0001", "L0100", "L01A1"])
def test_bad_codes_are_rejected(bad):
    with pytest.raises(LocationError):
        parse_location(bad)
