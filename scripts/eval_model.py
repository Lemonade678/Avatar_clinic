"""Score a packaging model on held-out photos: mAP@50, mAP@50:95, precision/recall/F1, count accuracy, inference time.

Usage (PowerShell or Git Bash):
  .venv/Scripts/python scripts/eval_model.py <test-folder>                          # Roboflow, cv.model from config.yaml
  .venv/Scripts/python scripts/eval_model.py <test-folder> --model stock-count-packaging/2
  .venv/Scripts/python scripts/eval_model.py <test-folder> --predictions preds.json # any model, offline
<test-folder> = the "test" folder of a Roboflow export in "COCO" format (photos + _annotations.coco.json).
--predictions takes COCO results JSON ([{image_id, category_id, bbox, score}]), e.g. from a model run elsewhere.
The scores are printed and saved as <test-folder>/eval-<model>-<date>.json so models can be compared later.
Photos go to Roboflow (US) only in the first two forms — the same place the app sends them.
"""
import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from stockcount.config import load_config
from stockcount.cv import CvUnavailable
from stockcount.metrics import ImageResult, coco_predictions, coco_truth, evaluate, latency_stats

TARGET_MAP50 = 0.80  # ณัฑฒ์'s bar (6/10)


def predict_with_roboflow(model: str, folder: Path, truth: dict) -> tuple[dict, list[float]]:
    from stockcount.roboflow import DEFAULT_URL, RoboflowClient

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        sys.exit("ROBOFLOW_API_KEY is not set (.env)")
    client = RoboflowClient(model, key, base_url=os.environ.get("ROBOFLOW_API_URL", DEFAULT_URL), timeout=30.0)
    boxes, timings = {}, []
    for image_id, (file_name, _) in truth.items():
        content = (folder / file_name).read_bytes()
        started = time.perf_counter()
        try:
            boxes[image_id] = tuple(client.detect(content, min_confidence=0.01))  # low: the whole PR curve
        except CvUnavailable as e:
            sys.exit(f"{file_name}: {e}")
        timings.append((time.perf_counter() - started) * 1000)
    return boxes, timings


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--model", help="Roboflow project/version (default: cv.model in config.yaml)")
    parser.add_argument("--predictions", type=Path, help="COCO results JSON instead of asking Roboflow")
    args = parser.parse_args(argv[1:])

    load_dotenv()
    cfg = load_config(os.environ.get("STOCKCOUNT_CONFIG", "config.yaml"))
    coco = json.loads((args.folder / "_annotations.coco.json").read_text(encoding="utf-8"))
    truth = coco_truth(coco)

    if args.predictions:
        model = args.predictions.stem
        predicted = coco_predictions(json.loads(args.predictions.read_text(encoding="utf-8")), coco)
        timings: list[float] = []
    else:
        model = args.model or cfg.cv.model
        predicted, timings = predict_with_roboflow(model, args.folder, truth)

    results = [ImageResult(boxes, predicted.get(image_id, ())) for image_id, (_, boxes) in truth.items()]
    score = evaluate(results, cfg.cv.min_confidence, cfg.cv.tolerance_ratio)
    latency = latency_stats(timings)

    verdict = "✅" if score.map50 >= TARGET_MAP50 else f"(target ≥ {TARGET_MAP50:.2f})"
    print(f"model {model} · {score.images} test photos · confidence ≥ {cfg.cv.min_confidence}")
    print(f"mAP@50     {score.map50:.3f} {verdict}")
    print(f"mAP@50:95  {score.map50_95:.3f}")
    print(f"precision  {score.precision:.3f} · recall {score.recall:.3f} · F1 {score.f1:.3f}")
    print(f"count accuracy {score.count_accuracy:.3f} (photos whose counts pass max(1, {cfg.cv.tolerance_ratio:.0%}))")
    if latency:
        print(f"inference  mean {latency['mean_ms']} ms · p50 {latency['p50_ms']:.0f} · p95 {latency['p95_ms']:.0f}"
              " (end to end: upload + model + answer)")
    print(f"{'class':<14}{'n':>5}{'AP50':>8}{'AP50:95':>9}{'P':>7}{'R':>7}{'F1':>7}")
    for c in score.classes:
        print(f"{c.cls:<14}{c.truth:>5}{c.ap50:>8.3f}{c.ap50_95:>9.3f}{c.precision:>7.3f}{c.recall:>7.3f}{c.f1:>7.3f}")

    out = args.folder / f"eval-{model.replace('/', '-')}-{date.today().isoformat()}.json"
    report = {
        "model": model,
        "date": date.today().isoformat(),
        "images": score.images,
        "min_confidence": cfg.cv.min_confidence,
        "map50": score.map50,
        "map50_95": score.map50_95,
        "precision": score.precision,
        "recall": score.recall,
        "f1": score.f1,
        "count_accuracy": score.count_accuracy,
        "latency": latency,
        "classes": [c.__dict__ for c in score.classes],
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main(sys.argv)
