"""Cross-check the counter against the small CV model, per packaging class. Pure: no I/O."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassCheck:
    packaging: str
    human: int
    cv: int
    ok: bool


@dataclass(frozen=True)
class CvCheck:
    status: str  # "ok" | "flagged" | "skipped"
    classes: tuple[ClassCheck, ...] = ()


SKIPPED = CvCheck("skipped")


def within_tolerance(human: int, cv: int, ratio: float) -> bool:
    # always allow at least one item of slack; bigger piles get a percentage
    return abs(cv - human) <= max(1, ratio * human)


def human_counts_by_class(counts: dict[str, int], packaging: dict[str, str]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for sku, qty in counts.items():
        if sku in packaging:
            totals[packaging[sku]] += qty
    return dict(totals)


def count_predictions(predictions: list[dict], min_confidence: float) -> dict[str, int]:
    return dict(Counter(p["class"] for p in predictions if p.get("confidence", 0) >= min_confidence))


def compare_cv(human: dict[str, int], cv: dict[str, int], ratio: float) -> CvCheck:
    classes = tuple(
        ClassCheck(c, human.get(c, 0), cv.get(c, 0), within_tolerance(human.get(c, 0), cv.get(c, 0), ratio))
        for c in sorted(set(human) | set(cv))
    )
    return CvCheck("ok" if all(c.ok for c in classes) else "flagged", classes)
