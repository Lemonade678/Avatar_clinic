"""Compare methods against L0 manual CVA and write an Obsidian report.

Inputs (CSV):
  L0:     image, subject, rater, tragus_x, tragus_y, c7_x, c7_y, cva   (from annotate.py)
  method: image, angle   (one CSV per method, e.g. MediaPipe proxy, YOLO-pose)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .metrics import summary, bland_altman, icc

def inter_rater(l0: pd.DataFrame):
    piv = l0.pivot_table(index="image", columns="rater", values="cva")
    return icc(piv.values) if piv.shape[1] >= 2 else None

def ba_plot(ax, ref, est, title):
    r, e = np.asarray(ref, float), np.asarray(est, float); m, d = (r + e) / 2, e - r
    ba = bland_altman(r, e)
    ax.scatter(m, d, s=10, alpha=.6, color="#1F3A68")
    for y, ls in [(ba["bias"], "-"), (ba["loa_low"], "--"), (ba["loa_high"], "--")]:
        ax.axhline(y, ls=ls, color="#E9A23B")
    ax.set_title(title, fontsize=9); ax.set_xlabel("mean of methods (deg)"); ax.set_ylabel("method - reference (deg)")

def report(ref: pd.Series, methods: dict, outdir, title, note=None, extra_md=None, l0=None):
    out = Path(outdir); (out / "attachments").mkdir(parents=True, exist_ok=True)
    rows = [summary(ref, est, name) for name, est in methods.items()]
    table = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, len(methods), figsize=(4.2 * len(methods), 3.4), squeeze=False)
    for ax, (name, est) in zip(axes[0], methods.items()):
        ba_plot(ax, ref, est, f"Bland-Altman: {name}")
    plt.tight_layout(); fig_name = "cva_bland_altman.png"; plt.savefig(out / "attachments" / fig_name, dpi=150); plt.close()
    lines = ["---", "tags: [cva, evaluation]", "---", f"# {title}", ""]
    if note: lines += [note, ""]
    lines += ["## ผลเทียบกับค่าอ้างอิง (L0)", "", table.to_markdown(index=False, floatfmt=".2f"), "",
              f"![[{fig_name}]]", "*เส้นทึบ = bias, เส้นประ = limits of agreement (±1.96 SD)*", ""]
    if l0 is not None:
        ir = inter_rater(l0)
        if ir: lines += [f"- Inter-rater ICC(2,1) ของ L0 = {ir['ICC(2,1)']:.2f} (n = {ir['n']} ภาพ, {ir['k']} ผู้วัด)", ""]
    lines += ["## วิธีอ่าน", "- **MAE** ยิ่งน้อยยิ่งดี · **ICC(2,1)** ≥ 0.75 = ดี, ≥ 0.90 = ดีมาก",
              "- **bias** ≠ 0 = คลาดเคลื่อนแบบมีทิศทาง (แก้ด้วย calibration ได้) · **LoA** กว้าง = คลาดเคลื่อนสุ่ม (แก้ด้วย calibration ไม่ได้)",
              "- **sens/spec@50** = ความสามารถแยกคอยื่น (CVA ≤ 50°)"]
    if extra_md: lines += ["", extra_md]
    lines += ["", "## ลิงก์", "- [[11 CVA Prototype]] · [[CVA and Pose Estimation]] · [[07 Solution Concepts - Pillar 2]]"]
    path = out / f"{title}.md"; path.write_text("\n".join(lines), encoding="utf-8")
    return path, table
