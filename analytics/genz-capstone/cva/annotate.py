"""L0 manual annotation tool (ground truth). Runs locally with a screen.

  python -m cva.annotate --images photos/ --out data/l0_annotations.csv --rater nutt

Click TRAGUS first, then C7.  keys: [n] save & next  [r] redo  [s] skip  [q] quit
Resumes automatically: images already annotated by this rater are skipped.
For inter-rater reliability, have a second person annotate with --rater <name>.
"""
import argparse, csv
from pathlib import Path
from .geometry import cva

MAX_W, MAX_H = 1400, 900

def display_scale(w, h, max_w=MAX_W, max_h=MAX_H):
    return min(1.0, max_w / w, max_h / h)

def to_original(pt, scale):
    return (pt[0] / scale, pt[1] / scale)

def main():
    import cv2
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--rater", required=True); ap.add_argument("--subject-from-prefix", action="store_true",
                    help="subject id = filename part before the first '_' (e.g. P01_front.jpg)")
    a = ap.parse_args()
    out = Path(a.out); done = set()
    if out.exists():
        with open(out, encoding="utf-8") as f:
            done = {(r["image"], r["rater"]) for r in csv.DictReader(f)}
    new_file = not out.exists()
    f = open(out, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=["image", "subject", "rater", "tragus_x", "tragus_y", "c7_x", "c7_y", "cva"])
    if new_file: w.writeheader()
    for p in sorted(Path(a.images).glob("*")):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png"} or (p.name, a.rater) in done:
            continue
        img = cv2.imread(str(p)); h, wd = img.shape[:2]; sc = display_scale(wd, h)
        base = cv2.resize(img, (int(wd * sc), int(h * sc))); pts = []
        def on_click(ev, x, y, *_):
            if ev == cv2.EVENT_LBUTTONDOWN and len(pts) < 2: pts.append((x, y))
        cv2.namedWindow("annotate"); cv2.setMouseCallback("annotate", on_click)
        while True:
            view = base.copy()
            for i, pt in enumerate(pts):
                cv2.circle(view, pt, 5, (0, 0, 255) if i == 0 else (255, 0, 0), -1)
            if len(pts) == 2:
                cv2.line(view, pts[0], pts[1], (0, 200, 0), 2)
                ang = cva(to_original(pts[0], sc), to_original(pts[1], sc))
                cv2.putText(view, f"CVA {ang:.1f} deg", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 0), 2)
            cv2.putText(view, "click TRAGUS then C7 | n=save r=redo s=skip q=quit", (20, view.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow("annotate", view); k = cv2.waitKey(20) & 0xFF
            if k == ord("r"): pts.clear()
            elif k == ord("s"): break
            elif k == ord("q"): f.close(); cv2.destroyAllWindows(); return
            elif k == ord("n") and len(pts) == 2:
                (tx, ty), (cx, cy) = to_original(pts[0], sc), to_original(pts[1], sc)
                subj = p.stem.split("_")[0] if a.subject_from_prefix else p.stem
                w.writerow({"image": p.name, "subject": subj, "rater": a.rater, "tragus_x": round(tx, 1),
                            "tragus_y": round(ty, 1), "c7_x": round(cx, 1), "c7_y": round(cy, 1),
                            "cva": round(cva((tx, ty), (cx, cy)), 2)})
                f.flush(); break
    f.close(); cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
