---
tags: [spec, code, avatar-clinic, hub]
aliases: [Core hub spec, spec ศูนย์กลาง repo บริษัท]
status: draft
status_note: "ฉบับ 6/10 — ณัฑฒ์ให้ทำแบบ freestyle ระหว่างไม่อยู่ · ตรวจผ่าน PR core-hub ก่อน merge"
created: 2026-10-06
---
# 🏛️ Spec — ศูนย์กลาง (core hub) ของ repo บริษัท `Avatar_clinic`

← [[Project - Avatar Clinic Hub]] · [[Code Hub - Avatar]] · 🇬🇧 English: [[2026-10-06-core-hub-design-en]]

## TL;DR
`main` = ศูนย์กลางของบริษัท: เอกสารที่ทุกระบบใช้ร่วมกัน + เครื่องมือภายใน (ระบบเช็คชื่อ part-time) + โค้ดวิเคราะห์ (capstone Gen Z) · บริการที่ deploy แยกและมีวงจรของตัวเอง (นับสต็อก) อยู่ branch ของตัวเอง แล้วลงทะเบียนไว้ในตาราง "Services" ของ README หน้าแรก

## ณัฑฒ์บอก vs Claude ตัดสินใจเอง
| ณัฑฒ์บอก (6/10) | Claude ตัดสินใจ (ณัฑฒ์ให้ freestyle) · เหตุผล |
|---|---|
| main = hub กลาง "อารมณ์ core หลัก" | โครง `tools/` `analytics/` `docs/` `.github/` — แยกตามชนิดงาน หาเจอง่าย |
| เอาระบบเช็คชื่อไปไว้ | **ย้าย** (ไม่คัดลอก) → `tools/checkin/` — มีที่เดียว ไม่ต้องแก้สองที่ |
| core = เอกสารศูนย์กลาง + โค้ด capstone | คัดลอกโค้ด capstone เฉพาะที่ commit แล้ว (commit `dd88055`) → `analytics/genz-capstone/` · **ไม่แตะ repo capstone เดิม** (มีงานที่ณัฑฒ์ยังไม่ commit อยู่) |
| ไลเซนส์ "ของบริษัท ห้ามใช้ภายนอก" (ตอบไว้สำหรับนับสต็อก) | ใช้กับ main ด้วย แทน Apache-2.0 — repo ทั้งก้อนเป็นของบริษัทแบบเดียวกัน |
| — | ทำบน branch `core-hub` → ณัฑฒ์ push แล้วเปิด PR เข้า main — ได้ตรวจ diff บน GitHub ก่อน merge |
| — | ยังไม่แยก "โค้ดกลาง" (เช่น ซ่อมพิมพ์ผิดภาษา) — ณัฑฒ์ไม่เลือกข้อนี้ และยังมีผู้ใช้แค่ระบบเดียว |

## โครงสร้าง
```
Avatar_clinic (main)
├── README.md                     แผนที่ทุกระบบ · เริ่มใช้ยังไง
├── LICENSE                       ของบริษัท ห้ามใช้ภายนอก
├── .github/
│   ├── CONTRIBUTING.md           วิธีทำงานร่วมกัน (branch · commit · PR · เทสต์ · เอกสาร)
│   ├── SECURITY.md               ความลับ · ข้อมูลส่วนบุคคล (PDPA) · ≤ 5 ประเทศ · แจ้งปัญหา
│   ├── CODEOWNERS · pull_request_template.md
│   └── workflows/ci.yml          เทสต์ checkin (Node) + analytics (Python)
├── tools/checkin/                ระบบเช็คชื่อ part-time → Google Sheet + Slack
├── analytics/genz-capstone/      survey · CVA · baseline (Python)
└── docs/specs/                   spec ของ hub (ไฟล์นี้)

branch ของบริการ: Stock-count-fork  ← นับสต็อก (แตกจาก main · deploy Railway)
```
- เก็บ `CONTRIBUTING.md` / `SECURITY.md` ไว้ใน `.github/` — GitHub ยังหาเจอ และ Obsidian ไม่เอาไปปนเป็นโน้ตในคลัง (ชื่อโน้ตต้องไม่ซ้ำ)

## ทำไมแบบนี้ (ทางเลือกที่ดู)
| ทางเลือก | ข้อดี | ข้อเสีย | ผล |
|---|---|---|---|
| **A. main = hub + tools + analytics · บริการ deploy แยก branch** | ตรงกับที่ณัฑฒ์อธิบาย · main อ่านเข้าใจง่าย · บริการ deploy อิสระ | branch บริการต้อง merge main เข้าไปเป็นระยะถ้าจะใช้ของกลาง | ✅ เลือก |
| B. รวมทุกอย่างใน main (`services/stock-count/`) | ที่เดียว · PR เดียวเห็นทุกอย่าง | ต้องย้าย path ของ CI / Railway / Supabase ของนับสต็อกกลาง pilot | ค่อยพิจารณาหลัง pilot |
| C. A + แยกโค้ดกลาง (core library) | ใช้ซ้ำได้ | มีผู้ใช้รายเดียว (YAGNI) · ณัฑฒ์ไม่เลือก | ❌ ตอนนี้ |

## กติกากลาง (ฉบับเต็มอยู่ใน `.github/CONTRIBUTING.md` และ `.github/SECURITY.md`)
- **branch:** `main` = hub · บริการ = branch ของตัวเองที่แตกจาก main (เช่น `Stock-count-fork`) · งานย่อย `feat/…` `fix/…` `docs/…` → PR
- **commit:** Conventional Commits (`feat:` `fix:` `docs:` `test:` `chore:` `ci:`) · ทุก PR ผ่าน CI · พฤติกรรมใหม่มาพร้อมเทสต์ที่เขียนก่อน
- **ข้อมูล:** ไหลผ่านได้ ≤ 5 ประเทศ (ตอนนี้ ไทย · ญี่ปุ่น · สิงคโปร์ · อเมริกา) · ข้อมูลส่วนบุคคล (PDPA: รูปคน เสียง ใบยินยอม คำตอบดิบ) ห้าม commit · ความลับอยู่ใน env / Script Properties / Railway variables เท่านั้น · repo เป็น private
- **เอกสาร:** spec/แผนลงวันที่ · ภาษาไทย = ต้นฉบับ + อังกฤษคู่กัน · README ภาษาอังกฤษ

## CI (`.github/workflows/ci.yml`)
- รันเมื่อมีการเปลี่ยนใน `tools/` `analytics/` หรือไฟล์ CI เอง (path filter — push ของบริการอื่นไม่เสียเวลารันงานนี้)
- **checkin:** Node 22 → `node --test "tools/checkin/tests/*.test.js"` (9 เทสต์)
- **analytics:** Python 3.12 → `pip install -r requirements.txt` → `pytest -q` (37 เทสต์ · ใช้ข้อมูลจำลอง เพราะข้อมูลจริงไม่อยู่ใน git)

## ความเสี่ยง / ยังไม่ได้ตรวจ ⚠️
- โค้ด capstone อยู่ 2 ที่ชั่วคราว (repo capstone เดิม + main) → ณัฑฒ์ตัดสินใจว่าจะลบ `code/` ใน capstone หรือเก็บไว้อ่านอย่างเดียว
- CI ยังไม่เคยรันบน GitHub · ⚠️ `opencv-python` ใน CI ไม่ถูกเรียกตอนเทสต์ (import ข้างในฟังก์ชัน) จึงไม่ต้องใช้ไลบรารีกราฟิกของเครื่อง
- ระบบเช็คชื่อที่ deploy อยู่ใน Google Apps Script ไม่ได้ผูกกับ git — แก้โค้ดใน repo แล้วต้องวางใหม่ใน Apps Script เอง

## ❓ ให้ณัฑฒ์ตัดสินใจตอนกลับมา
1. **merge PR `core-hub` เข้า main** ไหม (ตรวจ diff บน GitHub ก่อน)
2. **โค้ด capstone:** ลบ `code/` ใน repo capstone เดิม (ให้ main เป็นที่เดียว) หรือเก็บไว้
3. **ชื่อ branch บริการ:** ใช้แบบ `<Service>-fork` ต่อไปไหม หรือเปลี่ยนเป็น `service/<name>`
