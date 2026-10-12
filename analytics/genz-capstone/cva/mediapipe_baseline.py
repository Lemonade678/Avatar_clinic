"""L1 baseline: ear–shoulder proxy angle from MediaPipe Pose Landmarker (Tasks API).

Runs on YOUR machine (the model file is downloaded separately):
  1. pip install mediapipe
  2. download pose_landmarker_full.task from the MediaPipe Pose Landmarker model page
  3. python -m cva.mediapipe_baseline --model pose_landmarker_full.task --images photos/ --out outputs/l1_mediapipe.csv
NOTE: this proxy is NOT the CVA (no C7 landmark) — see simulate_proxy_bias.py.
"""
import argparse, csv
from pathlib import Path
from .geometry import ear_shoulder_proxy

L_EAR, R_EAR, L_SH, R_SH = 7, 8, 11, 12

def select_side(landmarks, width, height):
    """Pick the side facing the camera: the pair (ear, shoulder) with the higher
    minimum visibility. Returns dict with pixel coords + proxy angle."""
    sides = {"left": (L_EAR, L_SH), "right": (R_EAR, R_SH)}
    best = None
    for name, (e, s) in sides.items():
        vis = min(getattr(landmarks[e], "visibility", 1.0), getattr(landmarks[s], "visibility", 1.0))
        if best is None or vis > best[1]:
            best = (name, vis, e, s)
    name, vis, e, s = best
    ear = (landmarks[e].x * width, landmarks[e].y * height)
    sh = (landmarks[s].x * width, landmarks[s].y * height)
    return {"side": name, "visibility": vis, "ear_x": ear[0], "ear_y": ear[1],
            "sh_x": sh[0], "sh_y": sh[1], "proxy_angle": ear_shoulder_proxy(ear, sh)}

def run(model_path, image_dir, out_csv, min_visibility=0.5):
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    opts = vision.PoseLandmarkerOptions(base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
                                        running_mode=vision.RunningMode.IMAGE, num_poses=1)
    rows = []
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        for p in sorted(Path(image_dir).glob("*")):
            if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            img = mp.Image.create_from_file(str(p))
            res = lm.detect(img)
            if not res.pose_landmarks:
                rows.append({"image": p.name, "status": "no_person"}); continue
            r = select_side(res.pose_landmarks[0], img.width, img.height)
            r.update(image=p.name, status="ok" if r["visibility"] >= min_visibility else "low_visibility")
            rows.append(r)
    keys = ["image", "status", "side", "visibility", "ear_x", "ear_y", "sh_x", "sh_y", "proxy_angle"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, "") for k in keys})
    return rows

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--images", required=True)
    ap.add_argument("--out", default="outputs/l1_mediapipe.csv")
    a = ap.parse_args(); print(len(run(a.model, a.images, a.out)), "images →", a.out)
