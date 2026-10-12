"""Run every analysis in the survey plan and write an Obsidian-ready report.

Figures use English labels on purpose: matplotlib does not shape Thai text
(tone marks can land in the wrong place), so Thai stays in the markdown tables.
"""
import datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import codebook as cb
from . import stats as st

NAVY, TEAL, GREY, AMBER = "#1F3A68", "#2A9D8F", "#8D99AE", "#E9A23B"

def md(df, floatfmt=".2f"):
    return df.to_markdown(index=False, floatfmt=floatfmt)

def pct(x):
    return "–" if pd.isna(x) else f"{100 * x:.1f}%"

def ci_txt(p, lo, hi):
    return f"{pct(p)} (95% CI {pct(lo)}–{pct(hi)})"

class Report:
    def __init__(self, res, outdir, synthetic, fig_prefix="fig_"):
        self.d, self.res, self.syn = res.data, res, synthetic
        self.out = Path(outdir); self.out.mkdir(parents=True, exist_ok=True)
        self.figdir = self.out / "attachments"; self.figdir.mkdir(exist_ok=True)
        self.pre = fig_prefix
        self.lines, self.findings = [], {}

    # ---------- helpers ----------
    def h(self, t, lvl=2): self.lines += ["", "#" * lvl + " " + t, ""]
    def p(self, t=""): self.lines.append(t)
    def fig(self, name, caption):
        path = self.figdir / f"{self.pre}{name}.png"
        plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()
        self.p(f"![[{path.name}]]"); self.p(f"*{caption}*")

    # ---------- sections ----------
    def data_flow(self):
        f = self.res.flow
        self.h("1. ข้อมูลไหลจาก responses → analysed")
        self.p(md(pd.DataFrame([{"ขั้น": k, "n": v} for k, v in f.items()]), floatfmt=".0f"))
        if self.res.log:
            self.p(); self.p("**Log การทำความสะอาด**")
            for l in self.res.log: self.p(f"- {l}")
        d = self.d
        self.p(); self.p(f"อายุเฉลี่ย {d['age'].mean():.1f} ปี (SD {d['age'].std():.1f})")
        prof = d["A3"].value_counts(normalize=True).rename_axis("สถานะ").reset_index(name="สัดส่วน")
        prof["สัดส่วน"] = prof["สัดส่วน"].map(pct); self.p(); self.p(md(prof))

    def stages(self):
        d = self.d; n = int(d["stage"].notna().sum())
        self.h("2. RQ2 — ขนาดของ \"กลุ่มลังเล\" (TTM stage)")
        rows = []
        for s in range(1, 6):
            k = int((d["stage"] == s).sum()); p, lo, hi = st.wilson_ci(k, n)
            rows.append({"stage": f"{s} {cb.STAGE_NAMES[s]}", "n": k, "สัดส่วน (95% CI)": ci_txt(p, lo, hi)})
        self.p(md(pd.DataFrame(rows)))
        k = int(d["hesitant"].sum()); p, lo, hi = st.wilson_ci(k, n)
        self.findings["hesitant"] = (p, lo, hi, n)
        self.p(); self.p(f"> [!important] กลุ่มลังเล (stage 2+3) = **{ci_txt(p, lo, hi)}**, n = {n}")
        fig, ax = plt.subplots(figsize=(6.4, 3.2))
        counts = [int((d["stage"] == s).sum()) for s in range(1, 6)]
        colors = [GREY, AMBER, AMBER, TEAL, TEAL]
        ax.bar([cb.STAGE_NAMES[s] for s in range(1, 6)], counts, color=colors)
        ax.set_ylabel("respondents"); ax.set_title("Stage of change for neck care (amber = hesitant)")
        ax.tick_params(axis="x", labelsize=8)
        self.fig("stage", "การกระจายตัวตาม stage — สีส้มคือกลุ่มลังเล")

    def screen_pain(self):
        d = self.d
        self.h("3. เวลาหน้าจอ × อาการปวดคอ (12 เดือน)")
        rows = []
        for i, lab in enumerate(cb.ORDINAL["B1"]):
            g = d[d["B1"] == i]; k = int(g["C1_neck"].sum()); n = len(g)
            p, lo, hi = st.wilson_ci(k, n)
            rows.append({"มือถือ/วัน": lab, "n": n, "ปวดคอ 12 เดือน": ci_txt(p, lo, hi), "_p": p, "_lo": lo, "_hi": hi})
        t = pd.DataFrame(rows); self.p(md(t.drop(columns=["_p", "_lo", "_hi"])))
        table = pd.crosstab(d["B1"], d["C1_neck"])
        chi = st.chi2_with_cramers_v(table)
        rho = st.spearman(d["B1"], d["C1_neck"])
        o4 = st.odds_ratio(d["phone_ge4h"], d["C1_neck"]); o9 = st.odds_ratio(d["phone_ge9h"], d["C1_neck"])
        self.findings["or4"] = o4
        self.p(); self.p(f"- χ² = {chi['chi2']:.2f}, df = {chi['dof']}, p = {chi['p']:.4f}, Cramér's V = {chi['cramers_v']:.2f}"
                         + (f" ⚠️ {pct(chi['share_expected_lt5'])} ของช่องมี expected < 5" if chi['share_expected_lt5'] > .2 else ""))
        self.p(f"- แนวโน้ม (Spearman ρ) = {rho['rho']:.2f}, p = {rho['p']:.4f}")
        self.p(f"- OR มือถือ ≥4 ชม. = **{o4['or']:.2f}** (95% CI {o4['lo']:.2f}–{o4['hi']:.2f})")
        self.p(f"- OR มือถือ ≥9 ชม. = **{o9['or']:.2f}** (95% CI {o9['lo']:.2f}–{o9['hi']:.2f})")
        self.p("- เทียบกับงานไทย: จุดตัด ≥4 และ ≥9 ชม. ตั้งให้ตรงกับ [[Tech Neck - Thai Evidence]]")
        fig, ax = plt.subplots(figsize=(6.4, 3.2))
        x = np.arange(len(t)); ax.errorbar(x, t["_p"], yerr=[t["_p"] - t["_lo"], t["_hi"] - t["_p"]],
                                           fmt="o-", color=NAVY, capsize=4)
        ax.set_xticks(x, ["<2h", "2-4h", "4-6h", "6-9h", ">=9h"]); ax.set_ylim(0, 1)
        ax.set_ylabel("neck pain, past 12 months"); ax.set_xlabel("phone use per day")
        ax.set_title("Neck pain prevalence by phone time (95% Wilson CI)")
        self.fig("screen_neck", "ความชุกของอาการปวดคอตามชั่วโมงใช้มือถือ")

    def ttm_check(self):
        d = self.d
        self.h("4. ตรวจความสมเหตุสมผลตาม TTM")
        self.p("TTM คาดว่า: ข้อดี (pros) ↑, ข้อเสีย (cons) ↓, ความมั่นใจ (self-efficacy) ↑ ตาม stage")
        g = d.groupby("stage")[["pros", "cons", "self_efficacy", "decisional_balance"]].mean().reset_index()
        g["stage"] = g["stage"].astype(int).map(lambda s: f"{s} {cb.STAGE_NAMES[s]}")
        self.p(md(g))
        verdict = []
        for sc, sign in [("pros", 1), ("cons", -1), ("self_efficacy", 1)]:
            r = st.spearman(d["stage"], d[sc]); kw = st.kruskal_by_group(d[sc], d["stage"])
            ok = (np.sign(r["rho"]) == sign) and r["p"] < .05
            verdict.append(ok)
            self.p(f"- {sc}: ρ = {r['rho']:.2f} (p = {r['p']:.4f}), Kruskal–Wallis H = {kw['H']:.1f} (p = {kw['p']:.4f}) → {'✅ ตามทฤษฎี' if ok else '⚠️ ไม่ตามทฤษฎี'}")
        self.findings["ttm_ok"] = all(verdict)
        self.p(); self.p("> " + ("ข้อมูลสอดคล้องกับ TTM → ใช้การแบ่ง stage ต่อได้" if all(verdict)
                                 else "มีบาง scale ไม่ตามทฤษฎี → ตรวจถ้อยคำคำถาม/นิยาม 'การดูแลคอ' ก่อนใช้ผล"))
        fig, ax = plt.subplots(figsize=(6.4, 3.2))
        for sc, c in [("pros", TEAL), ("cons", AMBER), ("self_efficacy", NAVY)]:
            m = d.groupby("stage")[sc].mean(); ax.plot(m.index, m.values, "o-", color=c, label=sc)
        ax.set_xticks(range(1, 6), ["PC", "C", "P", "A", "M"]); ax.set_ylim(1, 5)
        ax.set_ylabel("mean score (1-5)"); ax.set_title("Decisional balance & self-efficacy by stage"); ax.legend(fontsize=8)
        self.fig("ttm", "ค่าเฉลี่ย pros / cons / self-efficacy ตาม stage")
        self.h("ความเชื่อมั่นของ scale (Cronbach's α)", 3)
        rows = [{"scale": k, "items": ", ".join(v), "α": st.cronbach_alpha(d[v])} for k, v in cb.SCALES.items()]
        self.p(md(pd.DataFrame(rows)))
        self.p("- α < 0.6 ในสเกล 2 ข้อเป็นเรื่องปกติ ให้รายงานตามจริง และพิจารณาเพิ่มข้อคำถามใน v1.0")

    def info_trust(self):
        d = self.d
        self.h("5. แหล่งข้อมูลสุขภาพ & ความเชื่อถือ")
        f1 = pd.DataFrame([{"แหล่ง": o, "เลือก": pct(d[f"F1__{o}"].mean())} for o in cb.MULTI["F1"]])
        self.p(md(f1))
        rows = []
        for th, key in cb.GRID_ROWS["F2"].items():
            m, lo, hi, n = st.mean_ci(d[f"F2_{key}"]); rows.append({"แหล่ง": th, "key": key, "mean": m, "lo": lo, "hi": hi})
        t = pd.DataFrame(rows).sort_values("mean", ascending=False)
        self.p(); self.p(md(t.rename(columns={"mean": "ความเชื่อถือเฉลี่ย", "lo": "CI ล่าง", "hi": "CI บน"}).drop(columns="key")))
        fig, ax = plt.subplots(figsize=(6.4, 3.0))
        ax.barh(t["key"], t["mean"], xerr=[t["mean"] - t["lo"], t["hi"] - t["mean"]], color=NAVY, capsize=3)
        ax.set_xlim(1, 5); ax.invert_yaxis(); ax.set_xlabel("trust (1-5)"); ax.set_title("Trust by source (95% CI)")
        self.fig("trust", "ความเชื่อถือแยกตามแหล่ง")

    def option_b(self):
        d = self.d
        self.h("6. Option B — Gen Z กับการดูแลสุขภาพพ่อแม่")
        k = int(d["helped_parents"].sum()); n = len(d); p, lo, hi = st.wilson_ci(k, n)
        self.findings["helped"] = (p, lo, hi)
        self.p(f"- เคยทำอย่างน้อย 1 อย่างให้พ่อแม่ใน 12 เดือน: **{ci_txt(p, lo, hi)}**")
        g2 = pd.DataFrame([{"การกระทำ": o, "สัดส่วน": pct(d[f'G2__{o}'].mean())} for o in cb.MULTI["G2"]])
        self.p(); self.p(md(g2))
        m, lo2, hi2, _ = st.mean_ci(d["G4"])
        self.p(); self.p(f"- ความตั้งใจส่งคลิปให้พ่อแม่ (G4) เฉลี่ย {m:.2f} (95% CI {lo2:.2f}–{hi2:.2f}); ตอบ 4–5 = {pct((d['G4'] >= 4).mean())}")
        g3 = d["G3"].value_counts(normalize=True).rename_axis("ผู้ตัดสินใจหลัก").reset_index(name="สัดส่วน")
        g3["สัดส่วน"] = g3["สัดส่วน"].map(pct); self.p(); self.p(md(g3))
        g5 = d["G5"].value_counts(normalize=True).rename_axis("ช่องทางส่ง").reset_index(name="สัดส่วน")
        g5["สัดส่วน"] = g5["สัดส่วน"].map(pct); self.p(); self.p(md(g5))
        g6 = pd.DataFrame([{"หัวข้อ": o, "สัดส่วน": pct(d[f'G6__{o}'].mean())} for o in cb.MULTI["G6"]])
        self.p(); self.p(md(g6))

    def ai_rules(self):
        d = self.d
        self.h("7. RQ3 — AI กับความเชื่อถือ")
        dist = d["H3"].value_counts().sort_index().rename_axis("H3 (1=ลดลงมาก…5=เพิ่มมาก)").reset_index(name="n")
        self.p(md(dist, floatfmt=".0f"))
        lower = (d["H3"] <= 2).mean(); self.findings["ai_lower"] = lower
        self.p(); self.p(f"- ความเชื่อถือ **ลดลง** เมื่อรู้ว่าใช้ AI (ตอบ 1–2): **{pct(lower)}**")
        h4 = pd.DataFrame([{"ส่วนที่ใช้ AI": o, "ยอมรับได้": d[f"H4__{o}"].mean()} for o in cb.MULTI["H4"]]).sort_values("ยอมรับได้", ascending=False)
        self.findings["ai_ok"] = h4.iloc[0]["ส่วนที่ใช้ AI"]
        h4["ยอมรับได้"] = h4["ยอมรับได้"].map(pct); self.p(); self.p(md(h4))
        self.p("- ใช้สร้าง **กฎการใช้ AI** ใน [[AI Disclosure and Trust]]: ส่วนที่ยอมรับ > 50% = ใช้ได้, < 20% = ห้ามใช้")

    def hesitant_profile(self):
        d = self.d
        self.h("8. โปรไฟล์กลุ่มลังเล vs คนอื่น")
        grp = d["hesitant"].map({1: "ลังเล", 0: "อื่น ๆ"})
        rows = []
        def add(label, s, kind="mean"):
            a, b = s[grp == "ลังเล"], s[grp == "อื่น ๆ"]
            rows.append({"ตัวแปร": label, "ลังเล": a.mean(), "อื่น ๆ": b.mean(), "ประเภท": kind})
        add("เชื่อคลิปแพทย์ตัวจริง (F2)", d["F2_doctor"]); add("เชื่อคำตอบ AI (F2)", d["F2_ai"])
        add("ตั้งใจส่งคลิปให้พ่อแม่ (G4)", d["G4"]); add("cons เฉลี่ย", d["cons"]); add("self-efficacy", d["self_efficacy"])
        add("ปวดคอ 12 เดือน", d["C1_neck"], "สัดส่วน"); add("เคยพบแพทย์/กายภาพ", d["sought_professional"], "สัดส่วน")
        t = pd.DataFrame(rows); self.p(md(t))
        pref = pd.crosstab(grp, d["H2"], normalize="index").map(pct).reset_index()
        self.p(); self.p("**อยากดูคลิปที่นำเสนอโดย (H2) แยกกลุ่ม**"); self.p(md(pref))
        self.p("- ใช้ตารางนี้เลือก **ใคร/อะไร** เป็นหน้าคอนเทนต์สำหรับกลุ่มลังเลใน [[07 Solution Concepts - Pillar 2]]")

    def open_ended(self):
        d = self.d
        self.h("9. คำตอบปลายเปิด — ธีมร่าง (ต้องให้คนตรวจ)")
        self.p("> [!warning] ธีมด้านล่างจับด้วยคำสำคัญเท่านั้น (keyword draft) → **ณัฑฒ์ต้องอ่านและแก้ทุกแถว** ในไฟล์ `open_ended_for_coding.csv` ก่อนสรุป")
        rows, export = [], d[["hesitant", "I1", "I2"]].copy()
        for q in cb.OPEN:
            for theme, kws in cb.THEMES.items():
                hit = d[q].apply(lambda s: any(k in s for k in kws)).astype(int)
                export[f"{q}_draft_{theme}"] = hit
                if hit.sum():
                    rows.append({"คำถาม": q, "ธีม (ร่าง)": theme, "ทั้งหมด": pct(hit.mean()),
                                 "เฉพาะกลุ่มลังเล": pct(hit[d["hesitant"] == 1].mean())})
            export[f"{q}_human_theme"] = ""
        self.p(md(pd.DataFrame(rows)))
        export.to_csv(self.out / "open_ended_for_coding.csv", index=False, encoding="utf-8-sig")

    def planning(self):
        self.h("10. วางแผนขนาดตัวอย่าง")
        self.p(md(st.ci_halfwidth_table(), floatfmt=".3f"))
        exposed_share = float(self.d["phone_ge4h"].mean()) if "phone_ge4h" in self.d else 0.8
        ns = [100, 200, 300, 400, 600]
        pw = [st.simulate_power_2x2(n, exposed_share=exposed_share, reps=800) for n in ns]
        self.p(); self.p(f"Power ในการเจอ OR = 2 (มือถือ ≥4 ชม. → ปวดคอ) เมื่อสัดส่วนคนใช้ ≥4 ชม. = {pct(exposed_share)} (สมมติฐานวางแผน):")
        self.p(md(pd.DataFrame({"n": ns, "power": pw}), floatfmt=".2f"))
        self.findings["power"] = dict(zip(ns, pw))
        fig, ax = plt.subplots(figsize=(6.0, 3.0))
        ax.plot(ns, pw, "o-", color=NAVY); ax.axhline(.8, ls="--", color=GREY)
        ax.set_ylim(0, 1); ax.set_xlabel("sample size"); ax.set_ylabel("power")
        ax.set_title("Power to detect OR=2 (>=4h phone vs neck pain)")
        self.fig("power", "power ตามขนาดตัวอย่าง — เส้นประ = 0.8")

    def build(self, title):
        f = self.findings
        head = ["---", "tags: [survey-report, " + ("synthetic" if self.syn else "real-data") + "]",
                f"generated: {dt.datetime.now():%Y-%m-%d %H:%M}", "source: avatar-research-code/survey", "---",
                f"# {title}", ""]
        if self.syn:
            head += ["> [!danger] ข้อมูลจำลอง (SYNTHETIC) — ใช้ทดสอบโปรแกรมเท่านั้น",
                     "> ตัวเลขทุกตัวในหน้านี้มาจากข้อมูลที่สร้างขึ้นเอง **ห้ามอ้างเป็นผลวิจัย** จนกว่าจะรันกับข้อมูลจริง", ""]
        summary = ["## สรุป 5 บรรทัด",
                   f"- กลุ่มลังเล: {ci_txt(*f['hesitant'][:3])}",
                   f"- OR มือถือ ≥4 ชม. → ปวดคอ: {f['or4']['or']:.2f} ({f['or4']['lo']:.2f}–{f['or4']['hi']:.2f})",
                   f"- TTM sanity check: {'ผ่าน' if f['ttm_ok'] else 'ไม่ผ่าน — ตรวจแบบสอบถาม'}",
                   f"- เคยช่วยพ่อแม่เรื่องสุขภาพ: {ci_txt(*f['helped'])}",
                   f"- ความเชื่อถือลดลงถ้ารู้ว่าใช้ AI: {pct(f['ai_lower'])} · ส่วนที่ยอมรับให้ AI ทำมากสุด: {f['ai_ok']}"]
        body = head + summary + self.lines + ["", "## ลิงก์", "- [[08 Gen Z Survey v0.1]] · [[10 Survey Analysis Pipeline]] · [[00 MOC - Avatar Gen Z Capstone]]"]
        path = self.out / f"{title}.md"
        path.write_text("\n".join(body), encoding="utf-8")
        return path

def run(res, outdir, synthetic, title):
    r = Report(res, outdir, synthetic)
    for step in (r.data_flow, r.stages, r.screen_pain, r.ttm_check, r.info_trust,
                 r.option_b, r.ai_rules, r.hesitant_profile, r.open_ended, r.planning):
        step()
    return r.build(title), r.findings
