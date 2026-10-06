"""SYNTHETIC survey generator — for testing the pipeline ONLY.

Produces a CSV shaped exactly like a Google Forms export of survey v0.1
(bracket-coded headers, ', '-joined multi-selects, grid columns).
The built-in relationships (screen time -> neck pain, stage -> pros/cons)
are ASSUMPTIONS chosen so the tests have something to find. They are NOT findings.
"""
import numpy as np
import pandas as pd
from . import codebook as cb

REGION_TH = {"neck": "คอ", "shoulder": "ไหล่", "upperback": "หลังส่วนบน"}

def header(code, text="", row=None):
    h = f"[{code}] {text}".strip()
    return f"{h} [{row}]" if row else h

def _multi(rng, options, p, max_k=None, exclusive=None):
    picks = [o for o, pi in zip(options, p) if rng.random() < pi]
    if exclusive and (not picks or rng.random() < 0.05):
        return exclusive
    if exclusive in picks and len(picks) > 1:
        picks.remove(exclusive)
    if max_k and len(picks) > max_k:
        picks = list(rng.choice(picks, max_k, replace=False))
    return ", ".join(picks)

def generate(n=200, seed=7, invalid_frac=0.05):
    rng = np.random.default_rng(seed)
    rows = []
    stage_p = [0.22, 0.30, 0.20, 0.13, 0.15]            # assumed
    open_bank_i1 = ["แพง ไม่รู้ว่าต้องจ่ายเท่าไหร่", "ไม่มีเวลา งานยุ่ง", "คิดว่ายังไม่หนัก เดี๋ยวก็หาย",
                    "ไม่รู้จะไปที่ไหนดี", "กลัวโดนขายคอร์ส", "ขี้เกียจ", ""]
    open_bank_i2 = ["ถ้าปวดมากจนทำงานไม่ได้", "เพื่อนแนะนำหรือมีรีวิวจริง", "ราคาชัดเจน มีโปร",
                    "ใกล้บ้าน จองออนไลน์ได้", "ถ้าหมอดูน่าเชื่อถือ", ""]
    for i in range(n):
        r = {"ประทับเวลา": f"2026/10/{1 + i % 28:02d} 10:{i % 60:02d}:00"}
        invalid = rng.random() < invalid_frac
        r[header("Q0_1", "ท่านยินยอม...")] = "ไม่ยินยอม" if invalid and rng.random() < .5 else "ยินยอม"
        age = int(rng.integers(20, 30))
        if invalid and r[header("Q0_1", "ท่านยินยอม...")] == "ยินยอม":
            age = int(rng.choice([18, 19, 31]))
        r[header("Q0_2", "ท่านอายุ 20–29 ปีหรือไม่")] = "ใช่" if 20 <= age <= 29 else "ไม่ใช่"
        r[header("A1", "อายุ (ปี)")] = age
        r[header("A2", "เพศ")] = rng.choice(cb.SINGLE["A2"], p=[.45, .5, .05])
        r[header("A3", "สถานะปัจจุบัน")] = rng.choice(cb.SINGLE["A3"], p=[.35, .35, .12, .13, .05])
        r[header("A4", "พื้นที่อาศัย")] = rng.choice(cb.SINGLE["A4"], p=[.55, .25, .20])
        b1 = int(rng.choice(5, p=[.05, .15, .30, .30, .20]))
        r[header("B1", "ใช้มือถือเฉลี่ยวันละ")] = cb.ORDINAL["B1"][b1]
        r[header("B2", "ใช้คอมพิวเตอร์/แท็บเล็ตเฉลี่ยวันละ")] = cb.ORDINAL["B2"][int(rng.choice(5, p=[.2, .2, .25, .2, .15]))]
        r[header("B3", "ท่าที่ใช้มือถือบ่อยที่สุด")] = rng.choice(cb.SINGLE["B3"], p=[.45, .35, .1, .1])
        r[header("B4", "ลุกหรือพักบ่อยแค่ไหน")] = cb.ORDINAL["B4"][int(rng.choice(4, p=[.15, .35, .3, .2]))]
        # assumed: neck-pain probability rises with phone hours (logistic)
        p_neck = 1 / (1 + np.exp(-(-1.2 + 0.55 * b1)))
        neck = rng.random() < p_neck
        for reg in cb.REGIONS:
            has = neck if reg == "neck" else rng.random() < (0.35 + 0.25 * neck)
            r[header("C1", "ใน 12 เดือนที่ผ่านมา เคยมีอาการ", REGION_TH[reg])] = "ใช่" if has else "ไม่ใช่"
            r[header("C2", "อาการทำให้ทำกิจวัตรไม่ได้", REGION_TH[reg])] = "ใช่" if has and rng.random() < .3 else "ไม่ใช่"
            r[header("C3", "ใน 7 วันที่ผ่านมา มีอาการ", REGION_TH[reg])] = "ใช่" if has and rng.random() < .55 else "ไม่ใช่"
            r[header("C4", "ความรุนแรงตอนนี้", REGION_TH[reg])] = int(np.clip(rng.normal(4.5, 2), 1, 10)) if has else 0
        r[header("C5", "เคยไปรับการดูแลเพราะอาการนี้หรือไม่")] = _multi(
            rng, cb.MULTI["C5"], [0, .12, .08, .30, .30, .03], exclusive="ไม่เคย")
        stage = int(rng.choice([1, 2, 3, 4, 5], p=stage_p))
        stage_txt = {v: k for k, v in cb.STAGES.items()}[stage]
        r[header("D1", "ข้อใดตรงกับท่านมากที่สุด")] = stage_txt
        # assumed TTM pattern: pros & self-efficacy rise, cons fall with stage
        lik = lambda mu: int(np.clip(round(rng.normal(mu, 0.9)), 1, 5))
        for e in ["E1", "E2"]:
            r[header(e)] = lik(2.8 + 0.35 * (stage - 1))
        for e in ["E3", "E4", "E5"]:
            r[header(e)] = lik(3.9 - 0.35 * (stage - 1))
        for e in ["E6", "E7"]:
            r[header(e)] = lik(2.3 + 0.45 * (stage - 1))
        r[header("F1", "แหล่งข้อมูลสุขภาพหลัก")] = _multi(rng, cb.MULTI["F1"], [.6, .45, .35, .3, .5, .25, .2, .15], max_k=3)
        for src, mu in zip(cb.GRID_ROWS["F2"], [4.2, 2.8, 2.9, 3.6, 3.3]):
            r[header("F2", "ความน่าเชื่อถือ", src)] = lik(mu)
        r[header("F3", "เคยเจอข้อมูลสุขภาพผิด")] = rng.choice(cb.SINGLE["F3"], p=[.25, .5, .1, .15])
        r[header("F4", "เคยดูไลฟ์ถาม–ตอบสุขภาพกับแพทย์")] = rng.choice(cb.SINGLE["F4"], p=[.1, .35, .55])
        r[header("G1", "อายุของพ่อ/แม่")] = rng.choice(cb.SINGLE["G1"], p=[.1, .35, .4, .1, .05])
        r[header("G2", "สิ่งที่เคยทำให้พ่อแม่")] = _multi(rng, cb.MULTI["G2"], [.55, .5, .25, .3, 0], exclusive="ไม่เคย")
        r[header("G3", "ใครมีส่วนตัดสินใจ")] = rng.choice(cb.SINGLE["G3"], p=[.5, .1, .35, .05])
        r[header("G4", "จะส่งคลิปให้พ่อแม่")] = lik(3.7)
        r[header("G5", "ช่องทางที่ใช้ส่ง")] = rng.choice(cb.SINGLE["G5"], p=[.75, .1, .12, .03])
        r[header("G6", "หัวข้อที่อยากส่งให้พ่อแม่")] = _multi(rng, cb.MULTI["G6"], [.4, .5, .35, .35, .3, .2])
        r[header("H1", "ความยาวคลิปที่ชอบ")] = rng.choice(cb.SINGLE["H1"], p=[.3, .4, .22, .08])
        r[header("H2", "อยากดูคลิปที่นำเสนอโดย")] = rng.choice(cb.SINGLE["H2"], p=[.5, .25, .1, .15])
        r[header("H3", "ถ้ารู้ว่าคลิปทำด้วย AI")] = lik(2.4)
        r[header("H4", "ส่วนไหนใช้ AI ได้")] = _multi(rng, cb.MULTI["H4"], [.5, .45, .7, .2, .05, 0], exclusive="ไม่มีเลย")
        r[header("I1", "อะไรทำให้ยังไม่ไปพบผู้เชี่ยวชาญ")] = rng.choice(open_bank_i1)
        r[header("I2", "อะไรจะทำให้ตัดสินใจไป")] = rng.choice(open_bank_i2)
        rows.append(r)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    out = sys.argv[2] if len(sys.argv) > 2 else "data/SYNTHETIC_survey.csv"
    generate(n).to_csv(out, index=False, encoding="utf-8-sig")
    print("wrote", out)
