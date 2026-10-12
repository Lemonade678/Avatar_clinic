"""Turn L0 annotations into an Ultralytics YOLO-pose dataset (2 keypoints: tragus, C7).

Split is BY SUBJECT, never by image: photos of the same person must not appear
in both train and test, otherwise the test score is inflated (data leakage).
"""
import csv, random, shutil
from collections import defaultdict
from pathlib import Path
from PIL import Image

KPT_NAMES = ["tragus", "c7"]

def bbox_from_keypoints(pts, img_w, img_h, margin=0.6):
    """Head–neck box around the keypoints, expanded by `margin` x the keypoint span."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    x0, x1 = max(0, min(xs) - margin * span), min(img_w, max(xs) + margin * span)
    y0, y1 = max(0, min(ys) - margin * span), min(img_h, max(ys) + margin * span)
    return x0, y0, x1, y1

def yolo_line(tragus, c7, img_w, img_h, cls=0):
    x0, y0, x1, y1 = bbox_from_keypoints([tragus, c7], img_w, img_h)
    cx, cy, bw, bh = (x0 + x1) / 2 / img_w, (y0 + y1) / 2 / img_h, (x1 - x0) / img_w, (y1 - y0) / img_h
    kp = []
    for (x, y) in (tragus, c7):
        kp += [x / img_w, y / img_h, 2]          # visibility 2 = labelled & visible
    return " ".join([str(cls)] + [f"{v:.6f}" for v in (cx, cy, bw, bh)] + [f"{v:.6f}" if i % 3 != 2 else str(v) for i, v in enumerate(kp)])

def split_subjects(subjects, ratios=(0.7, 0.15, 0.15), seed=42):
    s = sorted(set(subjects)); random.Random(seed).shuffle(s)
    n = len(s); n_tr = max(1, round(ratios[0] * n)); n_va = max(1, round(ratios[1] * n)) if n > 2 else 0
    return {**{x: "train" for x in s[:n_tr]}, **{x: "val" for x in s[n_tr:n_tr + n_va]},
            **{x: "test" for x in s[n_tr + n_va:]}}

def build(annotations_csv, image_dir, out_dir, rater=None, seed=42):
    rows = list(csv.DictReader(open(annotations_csv, encoding="utf-8")))
    if rater:
        rows = [r for r in rows if r["rater"] == rater]
    assign = split_subjects([r["subject"] for r in rows], seed=seed)
    out = Path(out_dir); counts = defaultdict(int)
    for r in rows:
        part = assign[r["subject"]]
        (out / "images" / part).mkdir(parents=True, exist_ok=True); (out / "labels" / part).mkdir(parents=True, exist_ok=True)
        src = Path(image_dir) / r["image"]
        with Image.open(src) as im:
            w, h = im.size
        shutil.copy(src, out / "images" / part / r["image"])
        line = yolo_line((float(r["tragus_x"]), float(r["tragus_y"])), (float(r["c7_x"]), float(r["c7_y"])), w, h)
        (out / "labels" / part / (Path(r["image"]).stem + ".txt")).write_text(line + "\n")
        counts[part] += 1
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\n"
        "kpt_shape: [2, 3]\nflip_idx: [0, 1]\nnames:\n  0: head_neck\n"
        "# keypoints: 0 = tragus, 1 = C7\n")
    return dict(counts), assign
