"""Load a Google Forms CSV export and turn it into an analysis-ready table.

Every decision that drops or changes data is logged in `CleanResult.log`
so the report can show exactly how n went from 'responses' to 'analysed'.
"""
import re
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from . import codebook as cb

CODE_RE = re.compile(r"^\s*\[([A-Z][A-Z0-9_]*)\]")
ROW_RE = re.compile(r"\[([^\]]+)\]\s*$")

@dataclass
class CleanResult:
    data: pd.DataFrame
    flow: dict = field(default_factory=dict)       # screening counts
    log: list = field(default_factory=list)        # human-readable warnings

def rename_columns(df):
    mapping, unknown = {}, []
    for col in df.columns:
        m = CODE_RE.match(str(col))
        if not m:
            unknown.append(col); continue
        code = m.group(1)
        if code in cb.GRID_ROWS:
            rm = ROW_RE.search(col)
            row = rm.group(1).strip() if rm and rm.start() > m.end() else None
            suffix = cb.GRID_ROWS[code].get(row)
            if suffix is None:
                unknown.append(col); continue
            mapping[col] = f"{code}_{suffix}"
        else:
            mapping[col] = code
    return df.rename(columns=mapping), unknown

def _map_single(s, options, log, code):
    bad = sorted(set(s.dropna()) - set(options))
    if bad:
        log.append(f"{code}: ตัวเลือกไม่ตรง codebook {bad} → ตั้งเป็นค่าว่าง")
    return s.where(s.isin(options))

def _explode_multi(s, options, log, code):
    out = pd.DataFrame(0, index=s.index, columns=[f"{code}__{o}" for o in options])
    unknown = set()
    for idx, val in s.fillna("").astype(str).items():
        for part in [p.strip() for p in val.split(", ") if p.strip()]:
            if part in options:
                out.at[idx, f"{code}__{part}"] = 1
            else:
                unknown.add(part)
    if unknown:
        log.append(f"{code}: เจอคำตอบนอก codebook {sorted(unknown)} (ไม่นับ)")
    out[f"{code}__answered"] = (s.fillna("").astype(str).str.strip() != "").astype(int)
    return out

def clean(df_raw):
    log = []
    df, unknown = rename_columns(df_raw.copy())
    ignored = [c for c in unknown if c not in ("ประทับเวลา", "Timestamp")]
    if ignored:
        log.append(f"คอลัมน์ที่ไม่มีรหัส [..] ถูกข้าม: {ignored}")
    flow = {"responses": len(df)}

    # 1) consent + age screening (PDPA / target group)
    df = df[df[cb.CONSENT["code"]] == cb.CONSENT["yes"]]
    flow["consented"] = len(df)
    df = df[df[cb.AGE_SCREEN["code"]] == cb.AGE_SCREEN["yes"]]
    df["A1"] = pd.to_numeric(df["A1"], errors="coerce")
    bad_age = ~df["A1"].between(cb.AGE_MIN, cb.AGE_MAX)
    if bad_age.any():
        log.append(f"ตัดออก {int(bad_age.sum())} แถว: ตอบว่าอายุ 20–29 แต่กรอกอายุจริงนอกช่วง")
    df = df[~bad_age]
    flow["age_eligible"] = len(df)

    # 2) duplicates (identical answers apart from timestamp)
    content_cols = [c for c in df.columns if c not in ("ประทับเวลา", "Timestamp")]
    dup = df.duplicated(subset=content_cols)
    if dup.any():
        log.append(f"ตัดคำตอบซ้ำ {int(dup.sum())} แถว")
    df = df[~dup]

    out = pd.DataFrame(index=df.index)
    out["age"] = df["A1"]
    for code, opts in cb.SINGLE.items():
        if code in df:
            out[code] = _map_single(df[code], opts, log, code)
    for code, opts in cb.ORDINAL.items():
        if code in df:
            s = _map_single(df[code], opts, log, code)
            out[code] = s.map({o: i for i, o in enumerate(opts)})
            out[code + "_label"] = s
    # grids
    for code, rows in cb.GRID_ROWS.items():
        for suffix in rows.values():
            col = f"{code}_{suffix}"
            if col not in df:
                continue
            if code in ("C1", "C2", "C3"):
                out[col] = df[col].map(cb.YESNO)
            else:
                out[col] = pd.to_numeric(df[col], errors="coerce")
    # Likert
    for code in cb.LIKERT:
        if code in df:
            v = pd.to_numeric(df[code], errors="coerce")
            oob = v.notna() & ~v.between(1, 5)
            if oob.any():
                log.append(f"{code}: ค่านอกช่วง 1–5 จำนวน {int(oob.sum())} → ค่าว่าง")
            out[code] = v.where(~oob)
    # stage
    stage = df["D1"].map(cb.STAGES)
    if stage.isna().any():
        log.append(f"D1: ตอบไม่ตรงตัวเลือก {int(stage.isna().sum())} แถว")
    out["stage"] = stage
    out["stage_name"] = stage.map(cb.STAGE_NAMES)
    out["hesitant"] = stage.isin(cb.HESITANT_STAGES).astype(int).where(stage.notna())
    # scale scores (mean of items, require all items)
    for name, items in cb.SCALES.items():
        out[name] = out[items].mean(axis=1, skipna=False)
    out["decisional_balance"] = out["pros"] - out["cons"]
    # multi-selects
    for code, opts in cb.MULTI.items():
        if code in df:
            out = out.join(_explode_multi(df[code], opts, log, code))
    for code in cb.OPEN:
        if code in df:
            out[code] = df[code].fillna("").astype(str).str.strip()
    # derived
    out["phone_ge4h"] = (out["B1"] >= 2).astype(int).where(out["B1"].notna())
    out["phone_ge9h"] = (out["B1"] >= 4).astype(int).where(out["B1"].notna())
    out["any_upper_pain_12m"] = out[[f"C1_{r}" for r in cb.REGIONS]].max(axis=1)
    if "G2__answered" in out:
        acts = [f"G2__{o}" for o in cb.MULTI["G2"] if o != "ไม่เคย"]
        out["helped_parents"] = (out[acts].sum(axis=1) > 0).astype(int)
    if "C5__ไม่เคย" in out:
        out["sought_professional"] = out[["C5__แพทย์", "C5__นักกายภาพบำบัด"]].max(axis=1)
    flow["analysed"] = len(out)
    return CleanResult(out.reset_index(drop=True), flow, log)
