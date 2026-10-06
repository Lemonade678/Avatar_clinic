import math, csv
import numpy as np
import pytest
from PIL import Image
from cva.geometry import cva, ear_shoulder_proxy, classify_fhp
from cva.metrics import icc, bland_altman, classification, mae
from cva.mediapipe_baseline import select_side
from cva.yolo_pose_data import yolo_line, split_subjects, build
from cva.annotate import display_scale, to_original
from cva.simulate_proxy_bias import simulate, evaluate

def test_cva_45_degrees():
    assert cva((110, 90), (100, 100)) == pytest.approx(45.0)

def test_cva_mirror_invariant():
    assert cva((90, 60), (100, 100)) == pytest.approx(cva((110, 60), (100, 100)))

def test_cva_smaller_when_head_forward():
    assert cva((150, 60), (100, 100)) < cva((105, 40), (100, 100))

def test_proxy_is_same_formula():
    assert ear_shoulder_proxy((110, 90), (100, 100)) == pytest.approx(45.0)

def test_fhp_threshold():
    assert classify_fhp(50.0) and not classify_fhp(50.1)

def test_icc_matches_shrout_fleiss_1979():
    sf = [[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]]
    r = icc(sf)
    assert r["ICC(1,1)"] == pytest.approx(0.17, abs=0.01)
    assert r["ICC(2,1)"] == pytest.approx(0.29, abs=0.01)
    assert r["ICC(3,1)"] == pytest.approx(0.71, abs=0.01)

def test_bland_altman_constant_bias():
    ref = np.array([40, 45, 50, 55.0]); ba = bland_altman(ref, ref + 2)
    assert ba["bias"] == pytest.approx(2) and ba["sd"] == pytest.approx(0)

def test_classification_counts():
    c = classification([45, 55, 48, 60], [47, 52, 51, 49])
    assert (c["tp"], c["fn"], c["tn"], c["fp"]) == (1, 1, 1, 1)

class LM:
    def __init__(self, x, y, v): self.x, self.y, self.visibility = x, y, v

def test_select_side_uses_visible_side():
    lms = [LM(0, 0, 0)] * 33
    lms[7], lms[11] = LM(.5, .3, .2), LM(.5, .6, .9)      # left: ear hidden
    lms[8], lms[12] = LM(.55, .3, .95), LM(.5, .6, .9)    # right: both visible
    r = select_side(lms, 1000, 1000)
    assert r["side"] == "right" and r["ear_x"] == pytest.approx(550)

def test_yolo_line_normalised_and_in_range():
    parts = yolo_line((400, 300), (380, 420), 800, 600).split()
    assert parts[0] == "0" and len(parts) == 11
    vals = [float(v) for i, v in enumerate(parts[1:]) if i not in (6, 9)]
    assert all(0 <= v <= 1 for v in vals)
    assert float(parts[5]) == pytest.approx(0.5) and parts[7] == "2"

def test_split_is_by_subject_no_leakage():
    subj = [f"P{i:02d}" for i in range(20)] * 3
    a = split_subjects(subj)
    assert set(a.values()) == {"train", "val", "test"} and len(a) == 20

def test_build_dataset(tmp_path):
    imgs = tmp_path / "imgs"; imgs.mkdir()
    rows = []
    for i in range(6):
        name = f"P{i}_side.jpg"; Image.new("RGB", (640, 480)).save(imgs / name)
        rows.append({"image": name, "subject": f"P{i}", "rater": "nutt", "tragus_x": 330, "tragus_y": 150,
                     "c7_x": 300, "c7_y": 260, "cva": 0})
    ann = tmp_path / "l0.csv"
    with open(ann, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    counts, _ = build(ann, imgs, tmp_path / "ds")
    assert sum(counts.values()) == 6 and (tmp_path / "ds" / "data.yaml").exists()

def test_annotation_scale_roundtrip():
    s = display_scale(4000, 3000); assert s < 1
    assert to_original((100 * s, 50 * s), s) == pytest.approx((100, 50))

def test_simulation_trained_model_beats_proxy():
    e = evaluate(simulate(400, seed=3)).set_index("method")
    assert e.loc["L2_trained", "MAE"] < e.loc["L1_proxy_calibrated", "MAE"] < e.loc["L1_proxy_raw", "MAE"]
