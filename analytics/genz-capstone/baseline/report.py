"""Write the baseline as an Obsidian note (Thai tables, ⚠️ on unverified values)."""
import datetime as dt
import math
from pathlib import Path
import pandas as pd
from .inputs import POST_KEYS, AUDIENCE_KEYS
from .metrics import summarise

INPUT_LABELS = {
    "plays": "ยอดเล่น (plays/views)", "reach": "reach (ผู้ชม)", "views_3s": "ดูถึง 3 วินาที",
    "reactions": "รีแอค", "comments": "คอมเมนต์", "shares": "แชร์", "clicks": "คลิก",
    "dropoff_sec": "จุดเลิกดู (วินาที)",
}

def fmt(v, unit=""):
    if v is None or (isinstance(v, float) and math.isnan(v)): return "–"
    if unit == "%": return f"{v:.1f}%"
    if unit == "/1k": return f"{v:.2f}"
    if unit == "s": return f"0:{v:02.0f}"
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"

def flag(ok): return "✅ ยืนยันแล้ว" if ok else "⚠️ ยังไม่ยืนยัน"

def build(baseline, title="Baseline - Facebook Insights", today=None):
    today = today or dt.date.today().isoformat()
    per_post, summary = summarise(baseline)
    all_ok = all(m.verified for m, _ in summary if not math.isnan(m.value))  # missing != unverified
    n_posts = len(baseline.posts)
    L = ["---",
         "tags: [baseline, facebook-insights, data/internal]",
         f"generated: {today}",
         f"path: \"{baseline.path}\"",
         f"verified: {str(all_ok).lower()}",
         "source: avatar-research-code/baseline",
         "---",
         f"# {title}", ""]
    if not all_ok:
        L += ["> [!warning] มีตัวเลขที่ยังไม่ยืนยัน (⚠️)",
              "> ค่าที่ติด ⚠️ อ่านจากรูปถ่ายหน้าจอหรือยังไม่ได้เทียบกับไฟล์ export — **ห้ามใช้เป็นตัวเลขอ้างอิงในรายงานจนกว่าจะยืนยัน**",
              "> เมื่อได้ไฟล์ export ให้รัน `python run_baseline.py --export <file>` สคริปต์เดิมจะเขียนหน้านี้ทับ", ""]
    L += ["ค่าอ้างอิงก่อน pilot (pre-pilot baseline) สำหรับเทียบผลหลังทดลอง · ตัวชี้วัดมาจาก [[00a Research Questions]] · บริบทใน [[01 Problem Statement]] และ [[Reels Hook and Retention]]", ""]

    L += ["## 1. ค่า baseline", ""]
    rows = [{"ตัวชี้วัด": m.label, "ค่า": fmt(m.value, m.unit) + ("" if m.verified or math.isnan(m.value) else " ⚠️"),
             "n โพสต์": n if m.key.startswith(("retention", "shares", "comments", "dropoff")) else "–",
             "สูตร": f"`{m.formula}`", "สถานะ": "–" if math.isnan(m.value) else flag(m.verified)}
            for m, n in summary]
    L += [pd.DataFrame(rows).to_markdown(index=False), ""]
    if n_posts > 1:
        L += [f"ค่าที่เป็นอัตรา = **มัธยฐาน** ของ {n_posts} โพสต์ (ตารางรายโพสต์ในหัวข้อ 3)", ""]

    L += ["## 2. ค่าดิบที่ใช้คำนวณ", ""]
    if n_posts == 1:
        r = baseline.posts.iloc[0]
        raw = [{"ค่าดิบ": INPUT_LABELS[k], "ค่า": fmt(r[k]) + ("" if baseline.post_verified.get(k) or pd.isna(r[k]) else " ⚠️"),
                "ที่มา": baseline.sources.get(k, "–"), "หมายเหตุ": baseline.notes.get(k, "")}
               for k in POST_KEYS]
    else:
        raw = [{"ค่าดิบ": INPUT_LABELS[k], "ค่า": f"รวม {fmt(baseline.posts[k].sum())} (ว่าง {int(baseline.posts[k].isna().sum())} โพสต์)",
                "ที่มา": baseline.sources.get(k, "–"), "หมายเหตุ": baseline.notes.get(k, "")}
               for k in POST_KEYS]
    raw += [{"ค่าดิบ": "ผู้ติดตาม " + k.removeprefix("audience_pct_").replace("_plus", "+").replace("_", "–"),
             "ค่า": fmt(baseline.audience[k], "%") + ("" if baseline.audience_verified.get(k) else " ⚠️"),
             "ที่มา": baseline.sources.get(k, "–"), "หมายเหตุ": baseline.notes.get(k, "")}
            for k in AUDIENCE_KEYS if k in baseline.audience]
    L += [pd.DataFrame(raw).to_markdown(index=False), ""]

    if n_posts > 1:
        L += ["## 3. รายโพสต์", ""]
        wide = per_post.pivot(index="post_id", columns="key", values="value").reset_index()
        L += [wide.to_markdown(index=False, floatfmt=".2f"), ""]

    L += ["## ข้อควรระวังในการตีความ", ""]
    if n_posts == 1:
        L += ["- **n = 1 โพสต์** — Reel ที่ถูกเลือกมาโชว์ในที่ประชุมน่าจะเป็นตัวที่ผลดี (selection bias) → ใช้เป็นจุดตั้งต้นเท่านั้น baseline จริงควรเป็นมัธยฐานของโพสต์ช่วงก่อน pilot (Path A)"]
    L += ["- retention 3 วินาทีแสดง 2 แบบ เพราะยังไม่ยืนยันว่า \"ยอดดู\" กับ \"ผู้ชม\" ใน Insights คือ plays หรือ reach · ต้องเลือกนิยามเดียวให้ตรงกันทั้งก่อนและหลัง pilot",
          "- อัตราแชร์/คอมเมนต์ใช้ reach เป็นตัวหาร (ไม่ใช่ยอดเล่น) เพื่อไม่ให้การเล่นซ้ำของคนเดิมทำให้อัตราดูต่ำลง",
          "- % ผู้ติดตาม 18–24 เป็นสัดส่วน **ตลอดอายุเพจ** ไม่ใช่ผู้ชมของโพสต์ใดโพสต์หนึ่ง → ใน pilot ให้ดูอายุผู้ชมรายโพสต์ประกอบ",
          "- Insights นับช่วง 18–24 แต่กลุ่มเป้าหมายคือ 20–29 → ตัวเลขนี้เป็นตัวแทนโดยประมาณ (proxy) ไม่ใช่ขนาดกลุ่มเป้าหมายจริง", ""]
    if baseline.log:
        L += ["## Log การแปลงข้อมูล", ""] + [f"- {l}" for l in baseline.log] + [""]
    L += ["## แหล่งข้อมูล", ""]
    srcs = sorted({s for s in baseline.sources.values() if s})
    L += [f"{i}. {s}" for i, s in enumerate(srcs, 1)] or ["- –"]
    L += ["", f"*สร้างโดย `code/run_baseline.py` · Path {baseline.path}*", ""]
    return "\n".join(L), summary

def run(baseline, outdir, title="Baseline - Facebook Insights", today=None):
    text, summary = build(baseline, title, today)
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    path = out / f"{title}.md"
    path.write_text(text, encoding="utf-8")
    return path, summary
