"""Detection accuracy the COCO / instance-segmentation way (ณัฑฒ์ 6/10 round 4). Pure: no I/O.

- a prediction is a true positive when it overlaps a still-unmatched labelled object of the same class
  with IoU ≥ the threshold; confident predictions are matched first, each labelled object only once
- AP = area under COCO's 101-point interpolated precision–recall curve, per class
- mAP@50 = AP at IoU 0.50 averaged over the classes in the test set; mAP@50:95 = also averaged over
  IoU 0.50, 0.55 … 0.95 (rewards tight boxes)
- precision / recall / F1 at the app's own confidence threshold (cv.min_confidence) and IoU 0.50,
  summed over all classes: precision = no over-counting, recall = no under-counting
- count accuracy = share of photos whose per-class counts pass the app's max(1, 10%) rule — the number
  that tells whether the cross-check will cry wolf
Instance segmentation uses the same scores with mask IoU instead of box IoU.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .cv import within_tolerance

IOU_THRESHOLDS = tuple(round(0.5 + 0.05 * i, 2) for i in range(10))
RECALL_POINTS = tuple(i / 100 for i in range(101))
MAX_DETECTIONS = 100  # per image and class, as COCO


@dataclass(frozen=True)
class Box:
    cls: str
    x: float  # left
    y: float  # top
    w: float
    h: float
    score: float = 1.0


@dataclass(frozen=True)
class ImageResult:
    truth: tuple[Box, ...]
    predicted: tuple[Box, ...]


@dataclass(frozen=True)
class ClassScore:
    cls: str
    truth: int
    ap50: float
    ap50_95: float
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class Evaluation:
    images: int
    classes: tuple[ClassScore, ...]
    map50: float
    map50_95: float
    precision: float
    recall: float
    f1: float
    count_accuracy: float


def iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    inter = ix * iy
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def _match(truth: list[Box], predicted: list[Box], threshold: float) -> list[tuple[float, bool]]:
    """(score, true positive?) for each prediction of one class in one image."""
    used: set[int] = set()
    scored = []
    for p in sorted(predicted, key=lambda b: -b.score)[:MAX_DETECTIONS]:
        best, best_iou = None, threshold
        for i, t in enumerate(truth):
            if i not in used and (overlap := iou(p, t)) >= best_iou:
                best, best_iou = i, overlap
        if best is not None:
            used.add(best)
        scored.append((p.score, best is not None))
    return scored


def average_precision(scored: list[tuple[float, bool]], n_truth: int) -> float | None:
    if n_truth == 0:
        return None
    precision, recall, hits = [], [], 0
    for rank, (_, hit) in enumerate(sorted(scored, key=lambda s: -s[0]), start=1):
        hits += hit
        precision.append(hits / rank)
        recall.append(hits / n_truth)
    for i in range(len(precision) - 2, -1, -1):  # interpolate: best precision at this recall or beyond
        precision[i] = max(precision[i], precision[i + 1])
    total, j = 0.0, 0
    for r in RECALL_POINTS:
        while j < len(recall) and recall[j] < r:
            j += 1
        if j < len(recall):
            total += precision[j]
    return total / len(RECALL_POINTS)


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _ratio(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def evaluate(results: list[ImageResult], min_confidence: float = 0.5, tolerance_ratio: float = 0.10) -> Evaluation:
    labelled = sorted({b.cls for r in results for b in r.truth})
    predicted = sorted({b.cls for r in results for b in r.predicted})

    def split(r: ImageResult, cls: str) -> tuple[list[Box], list[Box]]:
        return [b for b in r.truth if b.cls == cls], [b for b in r.predicted if b.cls == cls]

    scores, tp_all, fp_all, fn_all = [], 0, 0, 0
    for cls in sorted(set(labelled) | set(predicted)):
        pairs = [split(r, cls) for r in results]
        n_truth = sum(len(t) for t, _ in pairs)
        aps = [average_precision([s for t, p in pairs for s in _match(t, p, th)], n_truth) for th in IOU_THRESHOLDS]
        confident = [s for t, p in pairs for s in _match(t, [b for b in p if b.score >= min_confidence], 0.5)]
        tp = sum(hit for _, hit in confident)
        fp, fn = len(confident) - tp, n_truth - tp
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
        if n_truth:  # as COCO: classes absent from the test set do not enter the mean
            precision, recall = _ratio(tp, tp + fp), _ratio(tp, n_truth)
            scores.append(ClassScore(cls, n_truth, aps[0], sum(aps) / len(aps), precision, recall, _f1(precision, recall)))

    passed = 0
    for r in results:
        truth = Counter(b.cls for b in r.truth)
        seen = Counter(b.cls for b in r.predicted if b.score >= min_confidence)
        passed += all(within_tolerance(truth[c], seen[c], tolerance_ratio) for c in set(truth) | set(seen))

    precision, recall = _ratio(tp_all, tp_all + fp_all), _ratio(tp_all, tp_all + fn_all)
    return Evaluation(
        images=len(results),
        classes=tuple(scores),
        map50=sum(c.ap50 for c in scores) / len(scores) if scores else 0.0,
        map50_95=sum(c.ap50_95 for c in scores) / len(scores) if scores else 0.0,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        count_accuracy=_ratio(passed, len(results)),
    )


def _categories(coco: dict) -> dict[int, str]:
    return {c["id"]: c["name"] for c in coco.get("categories", [])}


def coco_truth(coco: dict) -> dict[int, tuple[str, tuple[Box, ...]]]:
    """A Roboflow "COCO" export (_annotations.coco.json) -> image id -> (file name, labelled boxes)."""
    names = _categories(coco)
    boxes: dict[int, list[Box]] = {img["id"]: [] for img in coco["images"]}
    for a in coco.get("annotations", []):
        if not a.get("iscrowd"):
            boxes[a["image_id"]].append(Box(names[a["category_id"]], *a["bbox"]))
    return {img["id"]: (img["file_name"], tuple(boxes[img["id"]])) for img in coco["images"]}


def coco_predictions(results: list[dict], coco: dict) -> dict[int, tuple[Box, ...]]:
    """COCO results format ([{image_id, category_id, bbox, score}]) -> image id -> predicted boxes."""
    names = _categories(coco)
    boxes: dict[int, list[Box]] = {}
    for p in results:
        boxes.setdefault(p["image_id"], []).append(Box(names[p["category_id"]], *p["bbox"], score=p["score"]))
    return {image_id: tuple(b) for image_id, b in boxes.items()}


def latency_stats(milliseconds: list[float]) -> dict | None:
    """Mean and nearest-rank p50 / p95 of per-image inference times."""
    if not milliseconds:
        return None
    ordered = sorted(milliseconds)

    def rank(p: float):
        return ordered[max(0, math.ceil(p * len(ordered)) - 1)]

    return {
        "mean_ms": round(sum(ordered) / len(ordered), 1),
        "p50_ms": rank(0.50),
        "p95_ms": rank(0.95),
        "n": len(ordered),
    }
