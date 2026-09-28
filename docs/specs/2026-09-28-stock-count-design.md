---
tags: [spec, code, avatar-clinic, computer-vision]
aliases: [Stock Count spec, spec นับสต็อก]
status: draft
status_note: "รอณัฑฒ์รีวิว spec ก่อนเขียนแผน"
created: 2026-09-28
---
# 📦 Spec — ระบบนับสต็อกหลังร้านผ่าน LINE (POC)

← [[Project - Stock Count]] · [[Code Hub - Avatar]]

## TL;DR
พนักงานสาขาลาดพร้าวสแกน QR ที่ชั้นหลังร้าน → แชท LINE bot ส่งรายการสินค้าชั้นนั้น → พิมพ์ยอด (+แนบรูปได้) → เก็บลง Supabase รายวัน → ปิดรอบแล้ว bot สรุปรายการที่ **ไม่ตรงกับยอดในระบบ**
เฟส 1 = เก็บยอด + รูปชั้นแบบดิจิทัล (spec นี้) · เฟส 2 = YOLO นับจากรูป · เฟส 3 = ระบบเทรนตัวเองจากรูปที่พนักงานส่ง (เฟส 2–3 เขียน spec แยกภายหลัง) — รูปจากเฟส 1 คือ dataset ตั้งต้น

## เป้าหมาย / วัดผล
- เป้าหมายใหญ่ (ข้อ C): POC ใช้งานจริงหลังร้าน → เอาผลไปเสนอบริษัท
- ✅ เวลานับหลังร้านต่อรอบ **< 15 นาที** (จับเวลาแบบกระดาษ 1 รอบก่อนเริ่ม เพื่อเป็น baseline)
- ✅ ทุกวันที่นับ มีรอบนับใน Supabase ครบทุกชั้น
- ✅ ปิดรอบแล้วเห็นรายการยอดไม่ตรงทันทีในแชท
- ✅ มีรูปชั้นพร้อมยอดที่ยืนยันแล้ว สะสมไว้เทรน YOLO

## ขอบเขต
| ใน POC | นอก POC |
|---|---|
| หลังร้าน สาขาลาดพร้าว | หน้าร้าน, สาขาอื่น |
| LINE bot แชท (Python) | LIFF / หน้าเว็บ JS |
| QR ชั้นละ 1 อัน | QR ต่อสินค้า |
| ยอดตั้งต้นจากใบนับ 27/9/2026 (ถอดเป็น CSV) | ต่อระบบสต็อกเดิมอัตโนมัติ (อนาคต: export → import) |
| เก็บรูปชั้น (bot ขอรูปทุกชั้น) | YOLO / Roboflow (เฟส 2), เทรนตัวเองอัตโนมัติ (เฟส 3), Typhoon OCR (ตัดออก — QR แทนการอ่านป้าย) |

## สถาปัตยกรรม
```
[QR ที่ชั้น] --สแกนด้วยกล้อง LINE--> [แชท LINE OA] --webhook--> [FastAPI (Python)]
                                                                 │
                                                   service (กติกาทั้งหมด)
                                                                 │
                                              repo --> [Supabase Postgres + Storage]
```
- **Python 3.11+** ทั้งหมด: `fastapi`, `line-bot-sdk` (v3), `supabase` (supabase-py), `pyyaml`, `qrcode[pil]`, `pytest`
- config คนแก้ = `config.yaml` (มี comment ได้) · ความลับ = `.env` (ไม่ขึ้น GitHub)

## โครงโฟลเดอร์
```
stock-count/
├── config.yaml              # สาขา, allowlist, ผังชั้น → SKU
├── .env.example             # LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY
├── data/stock_2026-09-27.csv   # ถอดจากใบนับ (sku, name, category, back_qty, front_qty)
├── supabase/migrations/*.sql   # schema — source of truth อยู่ใน git
├── src/stockcount/
│   ├── config.py     # โหลด + validate config.yaml
│   ├── parser.py     # แปลงข้อความแชท → คำสั่ง (ไม่ยุ่ง I/O)
│   ├── service.py    # กติกา: เปิดรอบ, บันทึกยอด, สรุป
│   ├── repo.py       # คุย Supabase (มี FakeRepo สำหรับเทสต์)
│   ├── messages.py   # สร้างข้อความตอบกลับภาษาไทย
│   └── app.py        # FastAPI webhook + ตรวจลายเซ็น LINE
├── scripts/
│   ├── import_csv.py # CSV + config.yaml → Supabase
│   └── make_qr.py    # สร้าง PNG ป้าย QR พร้อมพิมพ์
└── tests/
```
แต่ละไฟล์มีหน้าที่เดียว — `parser` กับ `service` เทสต์ได้โดยไม่ต้องมี LINE หรือ Supabase

## ข้อมูล (Supabase)
| ตาราง | คอลัมน์หลัก | หมายเหตุ |
|---|---|---|
| `products` | `sku` PK, `name`, `category` | จาก CSV |
| `shelves` | `code` PK (เช่น `A2`), `label` | จาก config.yaml |
| `shelf_products` | `shelf_code`, `sku`, `position` | ลำดับที่ bot แสดง |
| `stock_snapshots` | `sku`, `back_qty`, `as_of` | ยอดในระบบ · POC มีชุดเดียว (27/9/2026) |
| `count_sessions` | `id`, `count_date` unique, `opened_at`, `closed_at` | รอบละวัน |
| `counts` | `session_id`, `shelf_code`, `sku`, `expected_qty`, `counted_qty`, `line_user_id`, `updated_at` | unique (session, sku) · นับซ้ำ = ทับค่าเดิม |
| `user_state` | `line_user_id` PK, `shelf_code`, `opened_at` | ชั้นที่ผู้ใช้เปิดอยู่ · หมดอายุ 10 นาที |
| `shelf_photos` | `session_id`, `shelf_code`, `storage_path`, `line_user_id` | ไฟล์อยู่ใน bucket `shelf-photos` |

- `expected_qty` คัดลอกจาก snapshot ตอนนับ → รายงานย้อนหลังไม่เพี้ยนแม้ snapshot เปลี่ยน
- เก็บแค่ LINE user ID ของพนักงาน ไม่เก็บชื่อ/เบอร์
- **Supabase ↔ GitHub:** GitHub Action รัน `supabase db push` เมื่อ push เข้า `main` — ณัฑฒ์ใช้ Supabase **free plan** จึงใช้ Action (รันบน GitHub ฟรี) แทน GitHub integration แบบ built-in

## config.yaml (ตัวอย่าง)
```yaml
branch: ladprao
allowed_line_user_ids: []   # ว่าง = ใครก็ได้ (ช่วงทดลอง); ใส่ ID = จำกัดเฉพาะคนในลิสต์
shelves:
  A1:
    label: "ชั้นเหล็กซ้าย แถว 1"
    skus: [HB0001, HB0003, HB0004]
  A2:
    label: "ชั้นเหล็กซ้าย แถว 2"
    skus: [NA0025, NA0026]
```
`import_csv.py` ปฏิเสธถ้า SKU ใน config ไม่มีใน CSV หรือ SKU ซ้ำหลายชั้น

## การใช้งานในแชท
1. **สแกน QR** → QR เป็นลิงก์ `https://line.me/R/oaMessage/<basic_id>/?ชั้น%20A2` → LINE เปิดแชทกับ bot พร้อมข้อความ `ชั้น A2` ในช่องพิมพ์ → พนักงานกดส่ง 1 ครั้ง
2. bot ตอบ:
   ```
   ชั้น A2 (ชั้นเหล็กซ้าย แถว 2) — 27/9
   1. ROZY Bag (15g.)   ระบบ 0
   2. CELEB Bag (15g.)  ระบบ 0
   พิมพ์ยอดตามลำดับ เว้นวรรค เช่น: 7 8
   แล้วถ่ายรูปชั้นส่งมา 1 รูป (พิมพ์ "ข้าม" ถ้าถ่ายไม่ได้)
   ```
3. พนักงานพิมพ์ `7 8` → bot ยืนยัน `✅ ชั้น A2 บันทึกแล้ว · ไม่ตรง: ROZY Bag (ระบบ 0 / นับ 7)`
4. หลังบันทึกยอด bot ขอรูปชั้น → ส่งรูป → ผูกกับชั้นล่าสุดที่ผู้ใช้คนนั้นเปิด (ภายใน 10 นาที) · พิมพ์ `ข้าม` = ไม่ส่งรูป (ยอดยังบันทึกอยู่ — รูปไม่บังคับ เพื่อไม่ให้การนับติดขัด)
5. พิมพ์ `สรุป` → bot ตอบชั้นที่นับแล้ว/ยังไม่นับ + รายการไม่ตรงทั้งหมด · พิมพ์ `ปิดรอบ` → ปิดรอบวันนี้

**แสดงยอดในระบบให้พนักงานเห็นตอนนับ** (ไม่ใช้ blind count) — ณัฑฒ์เลือกเพราะเชื่อมั่นในพนักงาน และนับได้เร็วกว่า · ดูเหตุผลเทียบใน [[R&D - Stock Count คู่แข่ง]]

**สถานะต่อผู้ใช้** (ชั้นที่เปิดอยู่) เก็บในตาราง `user_state` ของ Supabase ไม่เก็บในหน่วยความจำ เพื่อให้รอดการ restart เซิร์ฟเวอร์

## Error handling
| เหตุการณ์ | bot ตอบ |
|---|---|
| ชั้นที่ไม่มีใน config | `ไม่พบชั้น X — ลองสแกน QR ใหม่` |
| จำนวนตัวเลขไม่เท่ารายการ / ไม่ใช่ตัวเลข / ติดลบ | `ชั้นนี้มี N รายการ ต้องพิมพ์ N ตัวเลข เช่น …` (ไม่บันทึกอะไรเลย) |
| พิมพ์ยอดโดยยังไม่สแกนชั้น / เกิน 10 นาที | `สแกน QR ที่ชั้นก่อนนะครับ` |
| รอบวันนี้ปิดแล้ว | `รอบวันนี้ปิดแล้ว` |
| ผู้ใช้ไม่อยู่ใน allowlist | ไม่ตอบ + log |
| ลายเซ็น LINE ผิด | HTTP 400 |
| Supabase ล้ม | `บันทึกไม่สำเร็จ ลองอีกครั้ง` + log error · ไม่มีการบันทึกครึ่ง ๆ (ทั้งชั้นหรือไม่เลย) |

## การทดสอบ
- **unit (pytest):** `parser` (ทุกรูปแบบข้อความ), `service` กับ `FakeRepo` (เปิดรอบ, บันทึก, นับซ้ำทับ, สรุป, ปิดรอบ, หมดเวลา 10 นาที), `config` validation, `import_csv` กับ CSV ตัวอย่าง
- **webhook:** FastAPI `TestClient` + ลายเซ็นปลอมที่เซ็นด้วย secret ทดสอบ
- **smoke จริง:** รันเครื่องตัวเอง + ngrok → สแกน QR 1 ชั้นจริงจากมือถือ

## รันที่ไหน
- dev: เครื่องณัฑฒ์ + ngrok (LINE ต้องการ HTTPS)
- ❓ deploy จริง: ยังไม่เลือก (ตัวเลือก: Render / Railway / Fly.io / Cloud Run) — ต้องตอบ webhook ทันก่อน LINE timeout; ถ้าเจ้าที่ free tier หลับแล้วตื่นช้า ใช้ push message แทน reply ได้

## เฟส 2–3 (แค่ทิศทาง ไม่อยู่ใน spec นี้)
รูปใน `shelf-photos` + ยอดที่ยืนยัน → Roboflow ติด label → YOLO-seg → bot เติมยอดให้ แล้วพนักงานแค่ตอบ `ok` หรือแก้ตัวเลข · เริ่มจาก SKU ที่เห็นชัดจากรูป (ขวด/กระปุกหันหน้า, ซองตั้งเรียง) ก่อนของที่ซ้อนกัน (หนังสือ, ซองในตะกร้า)

**เฟส 3 — เทรนตัวเอง:** รูปใหม่ที่พนักงานส่ง + ยอดที่พนักงานยืนยัน/แก้ = label ใหม่อัตโนมัติ → สะสมครบเกณฑ์ → เทรนโมเดลรอบใหม่ → ใช้ตัวใหม่เฉพาะเมื่อแม่นกว่าตัวเดิมบนชุดทดสอบ (ไม่ปล่อยโมเดลที่แย่ลงขึ้นใช้งาน) · spec เฟส 1 ต้องเก็บรูปกับยอดคู่กันให้ครบ เพื่อให้เฟส 3 เป็นไปได้

## ❓ คำถามค้าง
- ❓ รหัสสินค้าหน้า 2–3 ของใบนับถูกตัดขอบซ้าย (เห็นแค่ `…013`, `…023`) → ✅ ตัดสินแล้ว: ใช้รหัสชั่วคราว `TEMP-<เลขท้ายที่เห็น>` (หรือ `TEMP-P<หน้า>-<ลำดับ>` ถ้าไม่เห็นเลขเลย) + คอลัมน์ `needs_review=true` ใน CSV · ณัฑฒ์แก้เป็นรหัสจริงทีหลัง
- ❓ สินค้าไหนอยู่ชั้นไหนหลังร้าน → ณัฑฒ์ต้องเดินจดผังชั้น (ใส่ใน `config.yaml`)
- ❓ ต้องขออนุญาตหัวหน้าก่อนแปะ QR ที่ชั้นไหม
- ❓ LINE OA ใช้บัญชีใหม่ของณัฑฒ์ หรือบัญชีบริษัท
- ❓ ที่ deploy (ดูหัวข้อ "รันที่ไหน")
