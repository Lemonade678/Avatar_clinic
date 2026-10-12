"""Baseline metrics. Pure functions: canonical inputs in, Metric rows out.

Definitions (fixed before the pilot so pre/post use the same formula):
- retention_3s_per_play  = views_3s / plays
- retention_3s_per_reach = views_3s / reach     (reported too while "views vs viewers" is unresolved)
- shares_per_1k_reach    = 1000 * shares / reach
- comments_per_1k_reach  = 1000 * comments / reach
- dropoff_sec            = where Insights says most viewers stop (read off the retention graph)
- audience_pct_18_24     = % of page audience aged 18-24 (lifetime, as shown by Insights)
"""
from dataclasses import dataclass
import math
import pandas as pd

@dataclass
class Metric:
    key: str
    label: str          # Thai label for the report table
    value: float        # NaN when inputs are missing / denominator is zero
    unit: str           # "%", "/1k", "s"
    formula: str
    inputs: tuple       # canonical input keys used
    verified: bool      # True only if every input is verified

RATIOS = [
    # key, label, numerator, denominator, scale, unit
    ("retention_3s_per_play", "ดูถึง 3 วินาที ÷ ยอดเล่น", "views_3s", "plays", 100, "%"),
    ("retention_3s_per_reach", "ดูถึง 3 วินาที ÷ reach (ผู้ชม)", "views_3s", "reach", 100, "%"),
    ("shares_per_1k_reach", "แชร์ต่อ reach 1,000", "shares", "reach", 1000, "/1k"),
    ("comments_per_1k_reach", "คอมเมนต์ต่อ reach 1,000", "comments", "reach", 1000, "/1k"),
]

def ratio(num, den, scale=1.0):
    if num is None or den is None or pd.isna(num) or pd.isna(den) or den == 0:
        return math.nan
    return scale * num / den

def post_metrics(row, verified):
    """row: mapping of canonical post keys -> number (NaN = missing)."""
    out = []
    for key, label, n, d, scale, unit in RATIOS:
        out.append(Metric(key, label, ratio(row.get(n), row.get(d), scale), unit,
                          f"{scale:g} × {n} / {d}" if scale != 1 else f"{n} / {d}",
                          (n, d), verified.get(n, False) and verified.get(d, False)))
    out.append(Metric("dropoff_sec", "จุดที่คนเลิกดู", float(row.get("dropoff_sec", math.nan)), "s",
                      "อ่านจากกราฟ retention", ("dropoff_sec",), verified.get("dropoff_sec", False)))
    return out

def audience_metrics(audience, verified):
    out = []
    for key, label in [("audience_pct_18_24", "ผู้ติดตามอายุ 18–24"), ("audience_pct_25_34", "ผู้ติดตามอายุ 25–34")]:
        out.append(Metric(key, label, float(audience.get(key, math.nan)), "%", "Insights: Age & gender",
                          (key,), verified.get(key, False)))
    return out

def summarise(baseline):
    """Per-post metric table + one summary row per metric (median across posts)."""
    rows = []
    for r in baseline.posts.to_dict("records"):
        for m in post_metrics(r, baseline.post_verified):
            rows.append({"post_id": r["post_id"], **m.__dict__})
    per_post = pd.DataFrame(rows)
    summary = []
    template = post_metrics({}, baseline.post_verified)
    for m in template:
        vals = per_post.loc[per_post["key"] == m.key, "value"].dropna()
        m.value = float(vals.median()) if len(vals) else math.nan
        summary.append((m, int(len(vals))))
    for m in audience_metrics(baseline.audience, baseline.audience_verified):
        summary.append((m, 1 if not math.isnan(m.value) else 0))
    return per_post, summary
