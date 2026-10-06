"""Load baseline inputs into one canonical shape.

Canonical post keys: plays, reach, views_3s, reactions, comments, shares, clicks, dropoff_sec.
Canonical audience keys: audience_pct_<bucket>, e.g. audience_pct_18_24 (percent, 0-100).

Every value carries `verified` so the report can put ⚠️ on anything derived from
unverified numbers (Path B values are unverified by definition).
"""
from dataclasses import dataclass, field
from pathlib import Path
import re
import pandas as pd

POST_KEYS = ["plays", "reach", "views_3s", "reactions", "comments", "shares", "clicks", "dropoff_sec"]
AGE_BUCKETS = ["13_17", "18_24", "25_34", "35_44", "45_54", "55_64", "65_plus"]
AUDIENCE_KEYS = [f"audience_pct_{b}" for b in AGE_BUCKETS]
MANUAL_COLUMNS = ["metric", "value", "verified", "source", "note"]

# Column names seen in Meta exports / the Thai UI. ⚠️ Guessed until checked against a real
# export: unmatched columns are reported, and `overrides` (CLI --map) fixes any mismatch.
EXPORT_ALIASES = {
    "post_id": ["post id", "permalink", "รหัสโพสต์"],
    "plays": ["views", "plays", "video views", "initial plays", "ยอดดู"],
    "reach": ["reach", "post reach", "การเข้าถึง", "ผู้ชม"],
    "views_3s": ["3-second video views", "3-second views", "3s views", "ยอดดูวิดีโอ 3 วินาที"],
    "reactions": ["reactions", "การแสดงความรู้สึก", "รีแอคชั่น"],
    "comments": ["comments", "ความคิดเห็น", "คอมเมนต์"],
    "shares": ["shares", "การแชร์", "แชร์"],
    "clicks": ["clicks", "total clicks", "คลิก"],
}


@dataclass
class Baseline:
    posts: pd.DataFrame                      # one row per post, canonical columns (NaN = missing)
    post_verified: dict                      # key -> bool
    audience: dict                           # audience key -> percent
    audience_verified: dict                  # audience key -> bool
    path: str                                # "A (export)" or "B (manual)"
    sources: dict = field(default_factory=dict)   # key -> source text
    notes: dict = field(default_factory=dict)     # key -> note text
    log: list = field(default_factory=list)       # mapping / cleaning decisions


def _bool(x):
    s = str(x).strip().lower()
    if s in {"1", "true", "yes", "y", "ใช่"}: return True
    if s in {"0", "false", "no", "n", "ไม่", "", "nan"}: return False
    raise ValueError(f"verified must be 0/1, got {x!r}")


def age_bucket(label):
    """'18-24', '18–24', 'Age 18 - 24' -> '18_24'; '65+' -> '65_plus'."""
    s = str(label)
    if re.search(r"65\s*\+", s): return "65_plus"
    m = re.search(r"(\d{2})\s*[-–—]\s*(\d{2})", s)
    if not m: raise ValueError(f"unrecognised age bucket: {label!r}")
    b = f"{m.group(1)}_{m.group(2)}"
    if b not in AGE_BUCKETS: raise ValueError(f"unknown age bucket: {label!r}")
    return b


# ---------- Path B ----------
def load_manual(path):
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    missing = [c for c in MANUAL_COLUMNS if c not in df.columns]
    if missing: raise ValueError(f"{path}: missing columns {missing}")
    unknown = sorted(set(df["metric"]) - set(POST_KEYS) - set(AUDIENCE_KEYS))
    if unknown: raise ValueError(f"{path}: unknown metrics {unknown}")
    dup = df["metric"][df["metric"].duplicated()].tolist()
    if dup: raise ValueError(f"{path}: duplicated metrics {dup}")
    vals = {r.metric: float(str(r.value).replace(",", "")) for r in df.itertuples()}
    ver = {r.metric: _bool(r.verified) for r in df.itertuples()}
    post = {k: vals.get(k, float("nan")) for k in POST_KEYS}
    return Baseline(
        posts=pd.DataFrame([{"post_id": "manual", **post}]),
        post_verified={k: ver.get(k, False) for k in POST_KEYS},
        audience={k: v for k, v in vals.items() if k in AUDIENCE_KEYS},
        audience_verified={k: v for k, v in ver.items() if k in AUDIENCE_KEYS},
        path="B (manual)",
        sources={r.metric: r.source for r in df.itertuples()},
        notes={r.metric: r.note for r in df.itertuples() if r.note},
    )


# ---------- Path A ----------
def _read_table(path):
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}: return pd.read_excel(p)
    return pd.read_csv(p, encoding="utf-8-sig")


def map_columns(columns, overrides=None):
    """Return ({canonical: original column}, [unmatched columns])."""
    overrides = overrides or {}
    norm = {str(c).strip().lower(): c for c in columns}
    mapping = {}
    for key, aliases in EXPORT_ALIASES.items():
        if key in overrides:
            if overrides[key] not in columns: raise ValueError(f"--map {key}: no column {overrides[key]!r}")
            mapping[key] = overrides[key]; continue
        for a in aliases:
            if a in norm: mapping[key] = norm[a]; break
    unmatched = [c for c in columns if c not in mapping.values()]
    return mapping, unmatched


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def load_export(path, audience_path=None, overrides=None):
    raw = _read_table(path)
    mapping, unmatched = map_columns(list(raw.columns), overrides)
    log = [f"{k} ← คอลัมน์ `{c}`" for k, c in mapping.items()]
    if unmatched: log.append("คอลัมน์ที่ไม่ได้ใช้: " + ", ".join(f"`{c}`" for c in unmatched))
    posts = pd.DataFrame({"post_id": raw[mapping["post_id"]].astype(str) if "post_id" in mapping
                          else [f"row{i + 1}" for i in range(len(raw))]})
    for k in POST_KEYS:
        posts[k] = _num(raw[mapping[k]]) if k in mapping else float("nan")
    mapped = [k for k in POST_KEYS if k in mapping]
    bad = int(posts[mapped].isna().any(axis=1).sum()) if mapped else 0
    if bad: log.append(f"{bad} แถวมีช่องว่างหรือค่าที่ไม่ใช่ตัวเลข → นับเป็นค่าว่าง")
    src = f"Insights export `{Path(path).name}`"
    aud, aud_log = ({}, [])
    if audience_path: aud, aud_log = load_audience(audience_path)
    return Baseline(
        posts=posts,
        post_verified={k: k in mapping for k in POST_KEYS},
        audience=aud, audience_verified={k: True for k in aud},
        path="A (export)",
        sources={**{k: src for k in mapping}, **{k: f"Insights export `{Path(audience_path).name}`" for k in aud}},
        log=log + aud_log,
    )


def load_audience(path):
    """Long table: one age-bucket column + one percent/share column (0-1 or 0-100).
    If a gender column splits rows, rows are summed per age bucket."""
    raw = _read_table(path)
    cols = {str(c).strip().lower(): c for c in raw.columns}
    age_col = next((cols[c] for c in cols if "age" in c or "อายุ" in c), None)
    pct_col = next((cols[c] for c in cols if any(w in c for w in ["percent", "%", "share", "สัดส่วน", "value"])), None)
    if age_col is None or pct_col is None:
        raise ValueError(f"{path}: need an age column and a percent column, got {list(raw.columns)}")
    d = pd.DataFrame({"bucket": raw[age_col].map(age_bucket),
                      "pct": _num(raw[pct_col].astype(str).str.rstrip("%"))})
    total = d["pct"].sum()
    log = []
    if d["pct"].max() <= 1:
        d["pct"] *= 100; log.append("สัดส่วนอายุเป็น 0–1 → คูณ 100")
        total *= 100
    if abs(total - 100) > 2: log.append(f"⚠️ สัดส่วนอายุรวม {total:.1f}% (ไม่ใช่ ~100%)")
    agg = d.groupby("bucket")["pct"].sum()
    return {f"audience_pct_{b}": float(v) for b, v in agg.items()}, log
