from stockcount.cv import compare_cv, count_predictions, human_counts_by_class, within_tolerance


def test_tolerance_is_at_least_one_item():
    assert within_tolerance(human=3, cv=4, ratio=0.10)  # 10% of 3 < 1, so 1 is allowed
    assert not within_tolerance(human=3, cv=5, ratio=0.10)


def test_tolerance_grows_with_the_count():
    assert within_tolerance(human=30, cv=27, ratio=0.10)
    assert not within_tolerance(human=30, cv=26, ratio=0.10)


def test_human_counts_are_summed_per_packaging_class():
    counts = {"HB0001": 9, "HB0004": 9, "HB0007": 8, "XX": 5}
    packaging = {"HB0001": "bottle", "HB0004": "bottle", "HB0007": "pouch"}  # XX has no class → ignored
    assert human_counts_by_class(counts, packaging) == {"bottle": 18, "pouch": 8}


def test_predictions_below_confidence_are_ignored():
    preds = [
        {"class": "bottle", "confidence": 0.91},
        {"class": "bottle", "confidence": 0.40},
        {"class": "pouch", "confidence": 0.77},
    ]
    assert count_predictions(preds, min_confidence=0.5) == {"bottle": 1, "pouch": 1}


def test_all_classes_within_tolerance_is_ok():
    check = compare_cv({"bottle": 15}, {"bottle": 14}, ratio=0.10)
    assert check.status == "ok"
    assert [(c.packaging, c.human, c.cv, c.ok) for c in check.classes] == [("bottle", 15, 14, True)]


def test_any_class_off_is_flagged():
    check = compare_cv({"bottle": 15, "pouch": 8}, {"bottle": 15, "pouch": 3}, ratio=0.10)
    assert check.status == "flagged"
    assert [c.packaging for c in check.classes if not c.ok] == ["pouch"]


def test_items_the_model_sees_but_nobody_entered_are_flagged():
    check = compare_cv({"bottle": 2}, {"bottle": 2, "box": 4}, ratio=0.10)
    assert check.status == "flagged"
