"""Small, dependency-light statistics used by the survey report.
Each function returns plain numbers so results are easy to audit."""
import numpy as np
import pandas as pd
from scipy import stats

def wilson_ci(k, n, conf=0.95):
    """Wilson score interval for a proportion (better than normal approx at small n)."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    z = stats.norm.ppf(0.5 + conf / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))

def mean_ci(x, conf=0.95):
    x = pd.Series(x).dropna().astype(float)
    n = len(x)
    if n < 2:
        return (x.mean() if n else np.nan, np.nan, np.nan, n)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.5 + conf / 2, n - 1)
    return (m, m - t * se, m + t * se, n)

def cronbach_alpha(items: pd.DataFrame):
    """Cronbach's alpha on complete cases. With 2 items this equals the
    Spearman–Brown-type estimate and is usually low — report it honestly."""
    X = items.dropna().astype(float)
    k = X.shape[1]
    if k < 2 or len(X) < 3:
        return np.nan
    item_var = X.var(axis=0, ddof=1).sum()
    total_var = X.sum(axis=1).var(ddof=1)
    return float(k / (k - 1) * (1 - item_var / total_var)) if total_var > 0 else np.nan

def chi2_with_cramers_v(table: pd.DataFrame):
    chi2, p, dof, expected = stats.chi2_contingency(table.values)
    n = table.values.sum()
    r, c = table.shape
    v = np.sqrt(chi2 / (n * (min(r, c) - 1))) if n and min(r, c) > 1 else np.nan
    low_expected = float((expected < 5).mean())
    return {"chi2": chi2, "p": p, "dof": dof, "cramers_v": v, "share_expected_lt5": low_expected}

def odds_ratio(exposed, outcome):
    """2x2 odds ratio with Woolf (log) CI; Haldane +0.5 correction if any cell is 0."""
    e, o = pd.Series(exposed), pd.Series(outcome)
    ok = e.notna() & o.notna()
    e, o = e[ok].astype(int), o[ok].astype(int)
    a = ((e == 1) & (o == 1)).sum(); b = ((e == 1) & (o == 0)).sum()
    c = ((e == 0) & (o == 1)).sum(); d = ((e == 0) & (o == 0)).sum()
    if min(a, b, c, d) == 0:
        a, b, c, d = a + .5, b + .5, c + .5, d + .5
    orr = (a * d) / (b * c)
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return {"or": orr, "lo": np.exp(np.log(orr) - 1.96 * se), "hi": np.exp(np.log(orr) + 1.96 * se),
            "cells": (a, b, c, d)}

def spearman(x, y):
    ok = pd.Series(x).notna() & pd.Series(y).notna()
    r, p = stats.spearmanr(pd.Series(x)[ok], pd.Series(y)[ok])
    return {"rho": float(r), "p": float(p), "n": int(ok.sum())}

def kruskal_by_group(values, groups):
    df = pd.DataFrame({"v": values, "g": groups}).dropna()
    samples = [g["v"].values for _, g in df.groupby("g") if len(g) > 0]
    if len(samples) < 2:
        return {"H": np.nan, "p": np.nan}
    H, p = stats.kruskal(*samples)
    return {"H": float(H), "p": float(p)}

def ci_halfwidth_table(ns=(30, 100, 200, 400), p=0.5):
    rows = []
    for n in ns:
        _, lo, hi = wilson_ci(round(p * n), n)
        rows.append({"n": n, "ค่ากลาง": p, "±(ครึ่งความกว้าง CI 95%)": (hi - lo) / 2})
    return pd.DataFrame(rows)

def simulate_power_2x2(n, p_unexposed=0.35, odds_ratio_true=2.0, exposed_share=0.8,
                       reps=2000, alpha=0.05, seed=1):
    """Monte-Carlo power to detect an OR with a chi-square test at sample size n.
    Inputs are PLANNING ASSUMPTIONS, not data."""
    rng = np.random.default_rng(seed)
    odds_u = p_unexposed / (1 - p_unexposed)
    p_exp = odds_u * odds_ratio_true / (1 + odds_u * odds_ratio_true)
    hits = 0
    for _ in range(reps):
        e = rng.random(n) < exposed_share
        o = np.where(e, rng.random(n) < p_exp, rng.random(n) < p_unexposed)
        t = np.array([[np.sum(e & o), np.sum(e & ~o)], [np.sum(~e & o), np.sum(~e & ~o)]])
        if (t.sum(axis=1) == 0).any() or (t.sum(axis=0) == 0).any():
            continue
        if stats.chi2_contingency(t)[1] < alpha:
            hits += 1
    return hits / reps
