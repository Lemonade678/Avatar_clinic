# Gen Z capstone analytics

Code for the Avatar Clinic × Gen Z neck-health capstone: survey pipeline, craniovertebral-angle (CVA) prototype and Facebook Insights baseline.

> **Provenance:** copied from the capstone repo `avatar-genz-project` (`code/`, commit `dd88055`) on 2026-10-06. Make changes here; the capstone copy is kept read-only until it is removed.
> Real data never enters git: `data/` holds only `.gitkeep`, and tests run on synthetic data. Paths below are relative to this folder. The original notes follow in Thai.

## avatar-research-code (ฉบับเดิม)

โค้ดประกอบโปรเจกต์ **อวตารคลินิก × Gen Z** (capstone-style) — 3 ส่วน:

| ส่วน | ทำอะไร | สถานะ |
|---|---|---|
| `survey/` | วิเคราะห์แบบสอบถาม v0.1 จาก Google Forms → รายงาน Obsidian | ✅ รันได้ ทดสอบด้วยข้อมูลจำลอง |
| `baseline/` | ค่าอ้างอิงก่อน pilot จาก Facebook Insights → `Baseline - Facebook Insights.md` | ✅ Path B (ตัวเลขจากรูปถ่าย ⚠️) · Path A รอไฟล์ export |
| `cva/` | Prototype วัดมุมคอ (CVA): L0 วัดมือ · L1 MediaPipe · L2 YOLO-pose + ตัวประเมินผล | ✅ แกนคำนวณ + simulation รันได้ · MediaPipe/YOLO รันบนเครื่องตัวเอง |

## เริ่มใช้
```bash
pip install -r requirements.txt
python -m pytest -q                  # 37 tests
python run_survey.py --demo          # ข้อมูลจำลอง → outputs/survey_report/
python run_cva_demo.py               # simulation → outputs/cva_report/
```

## ส่วน A — แบบสอบถาม
1. ใน Google Forms ขึ้นต้นทุกคำถามด้วยรหัสในวงเล็บ เช่น `[A1] อายุ (ปี)`, `[Q0_1] ท่านยินยอม...`
   - คำถามแบบตาราง (grid) ใช้ชื่อแถวตรงกับ `survey/codebook.py` เช่น แถว `คอ`, `ไหล่`, `หลังส่วนบน`
   - ข้อความตัวเลือกต้องตรงกับ codebook ทุกตัวอักษร (ถ้าไม่ตรง จะถูกแจ้งใน log ของรายงาน)
2. ดาวน์โหลด CSV จาก Google Forms → `python run_survey.py responses.csv --out <vault>/10\ Survey\ Results`
3. เปิดรายงานใน Obsidian · แก้ธีมปลายเปิดใน `open_ended_for_coding.csv` (คอลัมน์ `*_human_theme`)

การตัดสินใจทุกข้อที่ตัด/เปลี่ยนข้อมูลถูกบันทึกในหัวข้อ "Log การทำความสะอาด" ของรายงาน

## ส่วน B — มุมคอ (CVA)
| ระดับ | เครื่องมือ | คำสั่ง |
|---|---|---|
| L0 ค่าอ้างอิง | คลิก tragus → C7 | `python -m cva.annotate --images photos/ --out data/l0.csv --rater nutt` |
| L1 baseline | MediaPipe หู–ไหล่ | `python -m cva.mediapipe_baseline --model pose_landmarker_full.task --images photos/` |
| L2 โมเดลเอง | YOLO-pose 2 จุด | `build()` ใน `cva/yolo_pose_data.py` → `python train_yolo_pose.py --data .../data.yaml` |
| ประเมินผล | MAE, ICC(2,1), Bland–Altman, sens/spec@50° | `cva.evaluate.report(...)` |

**กติกาถ่ายรูป (สำคัญกว่าโมเดล):** กล้องตั้งระดับน้ำ, ถ่ายด้านข้างตรง ๆ, ระยะ ~1.5–2 ม., เห็นหูและโคนคอชัด, ท่าเดียวกันทุกคน (เช่น นั่งมองมือถือ 1 นาที แล้วค่อยถ่าย) และแบ่ง train/test **ตามคน** ไม่ใช่ตามรูป

## ส่วน C — Facebook Insights baseline
- **Path B (ตอนนี้):** แก้ค่าใน `data/baseline_manual.csv` (คอลัมน์ `metric,value,verified,source,note` · `verified=0` = ⚠️) → `python run_baseline.py --out ..`
- **Path A (ได้ไฟล์ export แล้ว):** `python run_baseline.py --export posts.xlsx --audience age.csv --out ..`
  - ชื่อคอลัมน์ export เดาจากหน้าจอ Meta (⚠️) — ดูหัวข้อ "Log การแปลงข้อมูล" ในรายงาน ถ้าจับคู่ผิดใช้ `--map reach="ชื่อคอลัมน์จริง"`
- สูตรตัวชี้วัดอยู่ใน docstring ของ `baseline/metrics.py` — ใช้สูตรเดียวกันทั้งก่อนและหลัง pilot

## ข้อควรระวัง
- ข้อมูล `data/SYNTHETIC_*` และรายงานที่ติดป้าย SYNTHETIC/SIMULATION **ไม่ใช่ผลวิจัย**
- รูปคน = ข้อมูลส่วนบุคคล (PDPA) — ขอความยินยอมก่อนถ่าย, อย่า commit รูปขึ้น GitHub
- เครื่องมือวัดมุมคอเป็น **เครื่องมือคัดกรอง/สร้างความตระหนัก** ไม่ใช่การวินิจฉัย
