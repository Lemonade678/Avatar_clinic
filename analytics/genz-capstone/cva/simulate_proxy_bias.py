"""Monte-Carlo: how wrong is the ear–shoulder proxy (MediaPipe L1) compared with true CVA?

Sagittal-plane model in centimetres, C7 at the origin, subject facing +x.
ALL anatomical numbers below are ILLUSTRATIVE ASSUMPTIONS for a what-if analysis,
not measured anthropometry. Replace them with your own L0 data once you have it.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .metrics import summary

@dataclass
class Assumptions:
    cva_mean: float = 48.0      # deg, true CVA of the population
    cva_sd: float = 6.0
    neck_len_mean: float = 13.0 # cm, C7 -> tragus distance
    neck_len_sd: float = 1.5
    sh_dx_range: tuple = (0.0, 6.0)    # cm, shoulder landmark anterior of C7
    sh_dy_range: tuple = (-8.0, -2.0)  # cm, shoulder landmark below C7
    rounded_shoulder_corr: float = 0.0 # >0: lower CVA -> more anterior shoulder
    noise_pose_cm: float = 0.5  # keypoint noise, generic pose model (assumed)
    noise_l2_cm: float = 0.3    # keypoint noise, trained tragus/C7 model (assumed target)

def _angle(upper, lower):
    dx = np.abs(upper[:, 0] - lower[:, 0]); dy = upper[:, 1] - lower[:, 1]
    return np.degrees(np.arctan2(dy, dx))

def simulate(n=400, a=Assumptions(), seed=0):
    rng = np.random.default_rng(seed)
    theta = rng.normal(a.cva_mean, a.cva_sd, n)
    r = rng.normal(a.neck_len_mean, a.neck_len_sd, n)
    c7 = np.zeros((n, 2))
    tragus = np.column_stack([r * np.cos(np.radians(theta)), r * np.sin(np.radians(theta))])
    u = rng.random(n)
    if a.rounded_shoulder_corr:
        z = (a.cva_mean - theta) / a.cva_sd       # forward head -> larger z
        u = np.clip(u * (1 - a.rounded_shoulder_corr) + a.rounded_shoulder_corr * (0.5 + z / 4), 0, 1)
    sh = np.column_stack([a.sh_dx_range[0] + u * (a.sh_dx_range[1] - a.sh_dx_range[0]),
                          rng.uniform(*a.sh_dy_range, n)])
    noise = lambda s: rng.normal(0, s, (n, 2))
    df = pd.DataFrame({"true_cva": theta})
    df["L1_proxy_raw"] = _angle(tragus + noise(a.noise_pose_cm), sh + noise(a.noise_pose_cm))
    df["L2_trained"] = _angle(tragus + noise(a.noise_l2_cm), c7 + noise(a.noise_l2_cm))
    # calibration: fit on first half, apply to second half (honest hold-out)
    half = n // 2
    b, c = np.polyfit(df["L1_proxy_raw"][:half], df["true_cva"][:half], 1)
    df["L1_proxy_calibrated"] = c + b * df["L1_proxy_raw"]
    df["split"] = ["calibration"] * half + ["test"] * (n - half)
    return df

def evaluate(df):
    t = df[df["split"] == "test"]
    rows = [summary(t["true_cva"], t[m], m) for m in ["L1_proxy_raw", "L1_proxy_calibrated", "L2_trained"]]
    return pd.DataFrame(rows)

def sensitivity(spreads=(0, 1, 2, 3, 4, 6, 8), n=600, seed=1):
    """How does between-person variation in shoulder position (dx spread, cm)
    limit what calibration can fix?"""
    out = []
    for s in spreads:
        a = Assumptions(sh_dx_range=(3 - s / 2, 3 + s / 2))
        e = evaluate(simulate(n, a, seed)).set_index("method")
        out.append({"shoulder_dx_spread_cm": s, "MAE_proxy_calibrated": e.loc["L1_proxy_calibrated", "MAE"],
                    "MAE_L2": e.loc["L2_trained", "MAE"]})
    return pd.DataFrame(out)
