import pytest

from stockcount.keyboard import EN_TO_TH, TH_TO_EN, UNITS, fix_layout, to_english, to_thai

VOCAB = ["อุระกาวาท", "MALA Madam Blossom", "MALA-mini", "กัณฑรา", *UNITS]


def test_thai_word_typed_on_english_layout():
    assert to_thai("v6itdk;km") == "อุระกาวาท"


def test_english_word_typed_on_thai_layout():
    assert to_english("ทฟสฟ") == "mala"
    assert to_english("ยฟแาฟเำ") == "package"


def test_number_only_tokens_are_left_alone():
    # a count typed on the number pad must stay a number in both directions
    assert to_thai("v6itdk;km 2 -;f") == "อุระกาวาท 2 ขวด"
    assert to_english("ทฟสฟ 2 ยฟแาฟเำ") == "mala 2 package"


# ณัฑฒ์'s own examples from the plan review
@pytest.mark.parametrize(
    "typed, meant",
    [
        ("v6itdk;km 2 -;f", "อุระกาวาท 2 ขวด"),
        ("ทฟสฟ 2 ยฟแาฟเำ", "mala 2 package"),
    ],
)
def test_fix_layout_repairs_wrong_layout(typed, meant):
    assert fix_layout(typed, VOCAB) == meant


@pytest.mark.parametrize("text", ["อุระกาวาท 2 ขวด", "MALA 3", "mala-mini 1 box", "7 8"])
def test_fix_layout_keeps_text_that_is_already_right(text):
    assert fix_layout(text, VOCAB) == text


def test_unknown_words_are_not_guessed():
    assert fix_layout("hello", VOCAB) == "hello"


def test_every_thai_key_maps_back():
    # each Thai character comes from exactly one key, so the reverse table is complete
    thai_outputs = [th for th in EN_TO_TH.values() if not th.isascii()]
    assert len(thai_outputs) == len(set(thai_outputs)) == len(TH_TO_EN)
