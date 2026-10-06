"""Run the CVA prototype end to end WITHOUT photos, using the Monte-Carlo simulation.
Output: an Obsidian report + figures under outputs/cva_report/.
With real data, use cva.evaluate.report(ref=L0 cva, methods={...}) instead."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cva.simulate_proxy_bias import simulate, sensitivity, Assumptions
from cva.evaluate import report

a = Assumptions()
df = simulate(600, a, seed=0); t = df[df["split"] == "test"]
sens = sensitivity()
out = "outputs/cva_report"
note = ("> [!danger] SIMULATION — ไม่ใช่ผลวัดจริง\n> ตัวเลขทั้งหมดมาจากสมมติฐานเชิงกายวิภาคที่ตั้งขึ้นเพื่อทดสอบแนวคิด "
        f"(CVA ~ N({a.cva_mean}, {a.cva_sd}), คอยาว ~ N({a.neck_len_mean}, {a.neck_len_sd}) cm, ไหล่อยู่หน้า C7 {a.sh_dx_range} cm, "
        f"ต่ำกว่า C7 {a.sh_dy_range} cm, noise pose {a.noise_pose_cm} cm, noise โมเดลเทรนเอง {a.noise_l2_cm} cm) — แทนด้วยข้อมูล L0 จริงเมื่อมี")
fig, ax = plt.subplots(figsize=(6, 3))
ax.plot(sens["shoulder_dx_spread_cm"], sens["MAE_proxy_calibrated"], "o-", label="L1 proxy + calibration", color="#E9A23B")
ax.plot(sens["shoulder_dx_spread_cm"], sens["MAE_L2"], "o-", label="L2 trained tragus+C7", color="#1F3A68")
ax.set_xlabel("between-person spread of shoulder position (cm)"); ax.set_ylabel("MAE (deg)")
ax.set_title("What calibration cannot fix"); ax.legend(fontsize=8); plt.tight_layout()
import pathlib; pathlib.Path(out, "attachments").mkdir(parents=True, exist_ok=True)
plt.savefig(f"{out}/attachments/cva_sensitivity.png", dpi=150); plt.close()
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4))
for ax, m in zip(axes, ["L1_proxy_raw", "L1_proxy_calibrated"]):
    ax.scatter(t["true_cva"], t[m], s=8, alpha=.6, color="#1F3A68"); lo, hi = 25, (100 if m.endswith("raw") else 80)
    ax.plot([lo, hi], [lo, hi], "--", color="grey"); ax.axvline(50, color="#E9A23B", lw=1); ax.axhline(50, color="#E9A23B", lw=1)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_xlabel("true CVA (deg)"); ax.set_ylabel(m); ax.set_title(m, fontsize=9)
plt.tight_layout(); plt.savefig(f"{out}/attachments/cva_proxy_scatter.png", dpi=150); plt.close()
extra = ("## ความไวต่อสมมติฐาน\n\n" + sens.to_markdown(index=False, floatfmt=".2f") +
         "\n\n![[cva_sensitivity.png]]\n*แม้ calibrate แล้ว ความต่างของตำแหน่งไหล่ระหว่างคนยังทำให้ MAE ติดเพดาน ~3–4° → เหตุผลที่ต้องหาจุด C7 โดยตรง*"
         "\n\n![[cva_proxy_scatter.png]]\n*ซ้าย: proxy ดิบสูงกว่าค่าจริงเกือบทุกจุด · ขวา: หลัง calibrate ยังกระจาย · เส้นส้ม = เกณฑ์ 50°*")
path, table = report(t["true_cva"], {m: t[m] for m in ["L1_proxy_raw", "L1_proxy_calibrated", "L2_trained"]},
                     out, "CVA Prototype Report (SIMULATION)", note=note, extra_md=extra)
print(table.round(2).to_string()); print("report:", path)
