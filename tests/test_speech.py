import pytest

from stockcount.speech import parse_english_number, parse_spoken, parse_thai_number

SLOT = [("HB0001", "อุระกาวาท"), ("HB0004", "อโธ"), ("HB0011", "อังมะ")]
MALA = [("HB0098", "MALA"), ("HB0116", "MALA Madam Blossom"), ("HB0121", "MALA-mini")]


@pytest.mark.parametrize(
    "word, value",
    [("ศูนย์", 0), ("เก้า", 9), ("สิบ", 10), ("สิบเอ็ด", 11), ("ยี่สิบ", 20), ("ยี่สิบห้า", 25),
     ("สามสิบ", 30), ("ร้อย", 100), ("หนึ่งร้อยยี่สิบ", 120), ("สองร้อย", 200)],
)
def test_thai_number_words(word, value):
    assert parse_thai_number(word) == value


@pytest.mark.parametrize(
    "words, value",
    [("zero", 0), ("two", 2), ("twelve", 12), ("twenty one", 21), ("twenty-one", 21),
     ("hundred", 100), ("one hundred five", 105)],
)
def test_english_number_words(words, value):
    assert parse_english_number(words) == value


def test_thai_sentence():
    assert parse_spoken("อุระกาวาท เก้า ขวด", SLOT) == {"HB0001": 9}


def test_thai_without_spaces_and_two_products():
    # speech-to-text often drops the spaces in Thai
    assert parse_spoken("อุระกาวาทเก้าขวดอโธ 3", SLOT) == {"HB0001": 9, "HB0004": 3}


def test_thai_digits():
    assert parse_spoken("อังมะ ๑๑", SLOT) == {"HB0011": 11}


def test_english_sentence_picks_the_longest_matching_name():
    assert parse_spoken("mala two", MALA) == {"HB0098": 2}
    assert parse_spoken("MALA madam blossom twelve", MALA) == {"HB0116": 12}
    assert parse_spoken("mala mini thirty", MALA) == {"HB0121": 30}


def test_name_without_its_bracket_part():
    assert parse_spoken("มะเร็งปอด ห้า", [("HB0045", "มะเร็งปอด(ต้ม)")]) == {"HB0045": 5}


def test_wrong_keyboard_layout_is_repaired_first():
    assert parse_spoken("v6itdk;km 2 -;f", SLOT) == {"HB0001": 2}


def test_name_without_a_number_is_skipped():
    assert parse_spoken("อุระกาวาท อโธ สอง", SLOT) == {"HB0004": 2}


def test_nothing_recognised():
    assert parse_spoken("สวัสดีครับ", SLOT) == {}
