import pytest

from stockcount.metrics import (
    Box,
    ImageResult,
    average_precision,
    coco_predictions,
    coco_truth,
    evaluate,
    iou,
    latency_stats,
)


def box(cls, x, y, w, h, score=1.0):
    return Box(cls, x, y, w, h, score)


# --- overlap ---------------------------------------------------------------------------------------
def test_iou_of_same_disjoint_and_half_shifted_boxes():
    a = box("jar", 0, 0, 10, 10)
    assert iou(a, a) == 1.0
    assert iou(a, box("jar", 20, 20, 5, 5)) == 0.0
    assert iou(a, box("jar", 5, 0, 10, 10)) == pytest.approx(1 / 3)  # 50 shared / 150 covered


# --- COCO-style scores --------------------------------------------------------------------------------
def test_perfect_predictions_score_one_everywhere():
    truth = (box("jar", 0, 0, 10, 10), box("bag", 20, 0, 10, 10))
    result = evaluate([ImageResult(truth, tuple(box(b.cls, b.x, b.y, b.w, b.h, 0.9) for b in truth))])
    assert (result.map50, result.map50_95) == (1.0, 1.0)
    assert (result.precision, result.recall, result.f1, result.count_accuracy) == (1.0, 1.0, 1.0, 1.0)


def test_loose_box_counts_at_iou_50_but_not_at_stricter_thresholds():
    # IoU 0.6: a hit at 0.50, 0.55 and 0.60, a miss at 0.65 … 0.95 -> mAP@50:95 = 3/10
    result = evaluate([ImageResult((box("jar", 0, 0, 10, 10),), (box("jar", 0, 0, 10, 6, 0.9),))])
    assert result.map50 == 1.0
    assert result.map50_95 == pytest.approx(0.3)


def test_right_box_with_the_wrong_class_is_a_miss_and_a_false_alarm():
    result = evaluate([ImageResult((box("jar", 0, 0, 10, 10),), (box("bag", 0, 0, 10, 10, 0.9),))])
    assert (result.map50, result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0, 0.0)


def test_average_precision_uses_the_101_point_interpolated_curve():
    # ranked: hit, false alarm, hit over 2 labelled objects -> precision 1, .5, .67 at recall .5, .5, 1
    ap = average_precision([(0.9, True), (0.8, False), (0.7, True)], n_truth=2)
    assert ap == pytest.approx((51 * 1 + 50 * 2 / 3) / 101)


def test_no_labelled_objects_means_no_average_precision():
    assert average_precision([(0.9, False)], n_truth=0) is None


def test_each_labelled_object_is_matched_once():
    # two predictions on one jar: the confident one hits, the other is a duplicate = false positive
    preds = (box("jar", 0, 0, 10, 10, 0.9), box("jar", 0, 0, 10, 10, 0.8))
    result = evaluate([ImageResult((box("jar", 0, 0, 10, 10),), preds)])
    assert (result.precision, result.recall) == (0.5, 1.0)


def test_precision_recall_f1_use_the_apps_confidence_threshold():
    # the 0.3 guess still helps the AP curve but the app would ignore it, so it is a miss for recall
    truth = (box("jar", 0, 0, 10, 10), box("jar", 20, 0, 10, 10))
    preds = (box("jar", 0, 0, 10, 10, 0.9), box("jar", 20, 0, 10, 10, 0.3))
    result = evaluate([ImageResult(truth, preds)], min_confidence=0.5)
    assert result.map50 == 1.0
    assert (result.precision, result.recall) == (1.0, 0.5)
    assert result.f1 == pytest.approx(2 / 3)


def test_count_accuracy_follows_the_apps_max_1_or_10_percent_rule():
    jars = tuple(box("jar", 12 * i, 0, 10, 10) for i in range(10))
    off_by_one = ImageResult(jars, tuple(box("jar", b.x, b.y, b.w, b.h, 0.9) for b in jars[:9]))
    missed_bags = ImageResult((box("bag", 0, 0, 10, 10), box("bag", 20, 0, 10, 10)), ())
    assert evaluate([off_by_one, missed_bags]).count_accuracy == 0.5


def test_per_class_scores_are_reported():
    result = evaluate([ImageResult((box("jar", 0, 0, 10, 10), box("bag", 20, 0, 10, 10)), (box("jar", 0, 0, 10, 10, 0.9),))])
    by_class = {c.cls: c for c in result.classes}
    assert (by_class["jar"].ap50, by_class["bag"].ap50, by_class["bag"].truth) == (1.0, 0.0, 1)
    assert result.map50 == 0.5


# --- reading a Roboflow "COCO" export and COCO-format predictions -------------------------------------
COCO = {
    "images": [{"id": 0, "file_name": "a.jpg"}, {"id": 1, "file_name": "b.jpg"}],
    "categories": [{"id": 0, "name": "packaging"}, {"id": 1, "name": "jar"}, {"id": 2, "name": "bag"}],
    "annotations": [
        {"image_id": 0, "category_id": 1, "bbox": [1, 2, 3, 4], "iscrowd": 0},
        {"image_id": 0, "category_id": 2, "bbox": [5, 6, 7, 8], "iscrowd": 0},
        {"image_id": 1, "category_id": 1, "bbox": [0, 0, 9, 9], "iscrowd": 1},  # crowd regions are not objects
    ],
}


def test_coco_ground_truth_by_image():
    truth = coco_truth(COCO)
    assert truth == {
        0: ("a.jpg", (Box("jar", 1, 2, 3, 4), Box("bag", 5, 6, 7, 8))),
        1: ("b.jpg", ()),
    }


def test_coco_predictions_by_image():
    preds = coco_predictions([{"image_id": 1, "category_id": 2, "bbox": [1, 1, 2, 2], "score": 0.7}], COCO)
    assert preds == {1: (Box("bag", 1, 1, 2, 2, 0.7),)}


# --- inference time ---------------------------------------------------------------------------------------
def test_latency_stats_in_milliseconds():
    stats = latency_stats([100, 120, 110, 300, 105])
    assert stats == {"mean_ms": 147.0, "p50_ms": 110, "p95_ms": 300, "n": 5}


def test_latency_stats_without_timings():
    assert latency_stats([]) is None
