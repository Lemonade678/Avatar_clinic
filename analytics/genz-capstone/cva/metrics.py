"""Agreement metrics for comparing a method against the manual reference (L0)."""
import numpy as np
import pandas as pd

def _xy(ref, est):
    r, e = np.asarray(ref, float), np.asarray(est, float)
    ok = ~(np.isnan(r) | np.isnan(e))
    return r[ok], e[ok]

def mae(ref, est):
    r, e = _xy(ref, est); return float(np.mean(np.abs(e - r)))

def rmse(ref, est):
    r, e = _xy(ref, est); return float(np.sqrt(np.mean((e - r) ** 2)))

def bland_altman(ref, est):
    r, e = _xy(ref, est); d = e - r
    bias, sd = float(d.mean()), float(d.std(ddof=1))
    return {"bias": bias, "sd": sd, "loa_low": bias - 1.96 * sd, "loa_high": bias + 1.96 * sd, "n": int(len(d))}

def icc(ratings):
    """Shrout & Fleiss (1979) ICCs from an (n_targets x k_raters) matrix.
    Returns ICC(1,1), ICC(2,1) absolute agreement, ICC(3,1) consistency.
    For method-vs-reference validity, report ICC(2,1)."""
    Y = np.asarray(ratings, float)
    Y = Y[~np.isnan(Y).any(axis=1)]
    n, k = Y.shape
    gm = Y.mean()
    ss_rows = k * ((Y.mean(axis=1) - gm) ** 2).sum()
    ss_cols = n * ((Y.mean(axis=0) - gm) ** 2).sum()
    ss_tot = ((Y - gm) ** 2).sum()
    ss_err = ss_tot - ss_rows - ss_cols
    bms = ss_rows / (n - 1); jms = ss_cols / (k - 1)
    ems = ss_err / ((n - 1) * (k - 1)); wms = (ss_cols + ss_err) / (n * (k - 1))
    return {
        "ICC(1,1)": (bms - wms) / (bms + (k - 1) * wms),
        "ICC(2,1)": (bms - ems) / (bms + (k - 1) * ems + k * (jms - ems) / n),
        "ICC(3,1)": (bms - ems) / (bms + (k - 1) * ems),
        "n": n, "k": k,
    }

def classification(ref_angle, est_angle, threshold=50.0):
    r, e = _xy(ref_angle, est_angle)
    tp = np.sum((r <= threshold) & (e <= threshold)); fn = np.sum((r <= threshold) & (e > threshold))
    tn = np.sum((r > threshold) & (e > threshold)); fp = np.sum((r > threshold) & (e <= threshold))
    sens = tp / (tp + fn) if tp + fn else np.nan; spec = tn / (tn + fp) if tn + fp else np.nan
    return {"sensitivity": float(sens), "specificity": float(spec), "accuracy": float((tp + tn) / len(r)),
            "tp": int(tp), "fn": int(fn), "tn": int(tn), "fp": int(fp)}

def summary(ref, est, name, threshold=50.0):
    ba = bland_altman(ref, est)
    ic = icc(np.column_stack(_xy(ref, est)))
    cl = classification(ref, est, threshold)
    return {"method": name, "n": ba["n"], "MAE": mae(ref, est), "RMSE": rmse(ref, est), "bias": ba["bias"],
            "LoA": f"{ba['loa_low']:.1f} to {ba['loa_high']:.1f}", "ICC(2,1)": ic["ICC(2,1)"],
            "sens@50": cl["sensitivity"], "spec@50": cl["specificity"]}
