---
tags: [spec, code, avatar-clinic, computer-vision, english]
aliases: [Stock Count spec (EN, 29/9), Stock Count design English (29/9)]
status: draft
status_note: "English companion of the 29/9 Thai spec — the Thai file is the source of truth if they ever differ"
created: 2026-09-29
---
# 📦 Spec — Back-store stock counting over LINE (POC)

← [[Project - Stock Count]] · [[Code Hub - Avatar]] · 🇹🇭 ภาษาไทย: [[2026-09-29-stock-count-design]] · 🕘 previous: [[2026-09-28-stock-count-design-en]]

## TL;DR
Staff at the MBK (มาบุญครอง) branch scan a QR code on a back-store shelf → a LINE chat bot lists the products on that shelf → staff type the counts (and can attach a photo for verification) → counts are stored in Supabase per day, so we can see which products sell best, summarised weekly → when the day is closed, the bot summarises every item that **does not match the system stock**.
Phase 1 = digital counts + shelf photos (this spec) + a mini object detection model · Phase 2 = YOLO counts from photos · Phase 3 = the model retrains itself from staff photos (phases 2–3 get their own specs later). Phase 1 photos are the starting dataset.

## Goals / success criteria
- Big goal: a POC used for real in the back store → results presented to the company
- ✅ Back-store counting time per round **< 10 minutes** (time one paper round first as the baseline)
- ✅ Every counting day has a session in Supabase covering every shelf
- ✅ Closing the session shows the mismatches in the chat immediately
- ✅ Shelf photos paired with confirmed counts accumulate for YOLO training

## Scope
| In the POC | Out of the POC |
|---|---|
| Back store, MBK branch | Front store, other branches |
| LINE chat bot (Python) | LIFF / JavaScript web front end |
| One QR per shelf | One QR per product |
| Starting stock from the 28/9/2026 count sheet (transcribed to CSV) | Automatic link to the existing stock system (later: export → import) |
| Shelf photos (bot asks for one per shelf) | YOLO / Roboflow (phase 2), self-training (phase 3), Typhoon OCR (dropped — QR replaces reading labels) |

## Architecture
```
[Shelf QR] --scan with LINE camera--> [LINE OA chat] --webhook--> [FastAPI (Python)]
                                                                   │
                                                      service (all the rules)
                                                                   │
                                                repo --> [Supabase Postgres + Storage]
```
- **Python 3.11+** throughout: `fastapi`, `line-bot-sdk` (v3), `supabase` (supabase-py), `pyyaml`, `qrcode[pil]`, `pytest`
- Human-edited config = `config.yaml` (comments allowed) · secrets = `.env` (never pushed to GitHub)

## Folder layout
```
stock-count/
├── config.yaml              # branch, LINE basic ID, allowlist, shelf → SKU layout
├── .env.example             # LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY
├── data/stock_2026-09-28.csv   # transcribed sheet (sku, name, category, back_qty, front_qty, system_qty, needs_review)
├── supabase/migrations/*.sql   # schema — the source of truth lives in git
├── src/stockcount/
│   ├── config.py     # load + validate config.yaml
│   ├── parser.py     # chat text → command (no I/O)
│   ├── service.py    # rules: open session, save counts, summarise
│   ├── repo.py       # talks to Supabase (InMemoryRepo for tests)
│   ├── messages.py   # Thai reply texts
│   └── app.py        # FastAPI webhook + LINE signature check
├── scripts/
│   ├── import_csv.py # CSV + config.yaml → Supabase
│   └── make_qr.py    # printable PNG QR labels
└── tests/
```
Each file has one job — `parser` and `service` are testable without LINE or Supabase.

## Data (Supabase)
| Table | Key columns | Notes |
|---|---|---|
| `products` | `sku` PK, `name`, `category` | from the CSV |
| `shelves` | `code` PK (e.g. `A2`), `label` | from config.yaml |
| `shelf_products` | `shelf_code`, `sku`, `position` | order the bot shows |
| `stock_snapshots` | `sku`, `back_qty`, `as_of` | system stock · the POC has one snapshot (28/9/2026) |
| `count_sessions` | `id`, `count_date` unique, `opened_at`, `closed_at` | one per day |
| `counts` | `session_id`, `shelf_code`, `sku`, `expected_qty`, `counted_qty`, `line_user_id`, `updated_at` | unique (session, sku) · a recount overwrites |
| `user_state` | `line_user_id` PK, `shelf_code`, `opened_at` | the shelf a user has open · expires after 10 minutes |
| `shelf_photos` | `session_id`, `shelf_code`, `storage_path`, `line_user_id` | files live in the `shelf-photos` bucket |

- `expected_qty` is copied from the snapshot at count time → historic reports stay correct even if the snapshot changes
- Only the staff member's LINE user ID is stored — no names or phone numbers
- **Supabase ↔ GitHub:** a GitHub Action runs `supabase db push` on pushes to `main`. ณัฑฒ์ is on the Supabase **free plan**, so the Action (free on GitHub) is used instead of the built-in GitHub integration

## config.yaml (example)
```yaml
branch: ladprao
line_basic_id: "@CHANGE-ME"   # LINE OA basic ID, used to build the QR links
allowed_line_user_ids: []     # empty = anyone (trial period); list IDs to restrict
shelves:
  A1:
    label: "ชั้นเหล็กซ้าย แถว 1"   # "left steel shelf, row 1"
    skus: [HB0001, HB0003, HB0004]
  A2:
    label: "ชั้นเหล็กซ้าย แถว 2"   # "left steel shelf, row 2"
    skus: [NA0025, NA0026]
```
`import_csv.py` refuses to run if a SKU in the config is missing from the CSV, or a SKU appears on more than one shelf.

## Chat flow
The bot speaks Thai to staff; English glosses are in brackets.
1. **Scan the QR** → the QR is the link `https://line.me/R/oaMessage/<basic_id>/?ชั้น%20A2` → LINE opens the bot chat with `ชั้น A2` ("shelf A2") pre-filled → staff tap send once
2. The bot replies:
   ```
   ชั้น A2 (ชั้นเหล็กซ้าย แถว 2) — 27/9
   1. ROZY Bag (15g.)   ระบบ 0          [system: 0]
   2. CELEB Bag (15g.)  ระบบ 0
   พิมพ์ยอดตามลำดับ เว้นวรรค เช่น: 7 8   [type counts in order, space-separated]
   แล้วถ่ายรูปชั้นส่งมา 1 รูป (พิมพ์ "ข้าม" ถ้าถ่ายไม่ได้)   [then send one shelf photo, or type "skip"]
   ```
3. Staff type `7 8` → the bot confirms `✅ ชั้น A2 บันทึกแล้ว · ไม่ตรง: ROZY Bag (ระบบ 0 / นับ 7)` [saved · mismatch: system 0 / counted 7]
4. After saving, the bot asks for a shelf photo → the photo is attached to the shelf that user last opened (within 10 minutes) · typing `ข้าม` [skip] sends no photo (the counts stay saved — photos are optional so counting never gets stuck)
5. `สรุป` [summary] → counted vs not-yet-counted shelves + every mismatch · `ปิดรอบ` [close] → closes today's session

**Staff see the system quantity while counting** (no blind count) — ณัฑฒ์ chose this out of trust in the staff, and it is faster · the trade-off is discussed in [[R&D - Stock Count คู่แข่ง]]

**Per-user state** (the open shelf) lives in the Supabase `user_state` table, not in memory, so it survives a server restart.

## Error handling
| Event | Bot reply |
|---|---|
| Shelf not in the config | `ไม่พบชั้น X — ลองสแกน QR ใหม่` [shelf X not found — scan again] |
| Wrong number of values / not numbers / negative | `ชั้นนี้มี N รายการ ต้องพิมพ์ N ตัวเลข เช่น …` [this shelf has N items, type N numbers] (nothing is saved) |
| Counts typed without scanning / after 10 minutes | `สแกน QR ที่ชั้นก่อนนะครับ` [scan the shelf QR first] |
| Today's session already closed | `รอบวันนี้ปิดแล้ว` [today's session is closed] |
| User not on the allowlist | no reply + log |
| Wrong LINE signature | HTTP 400 |
| Supabase down | `บันทึกไม่สำเร็จ ลองอีกครั้ง` [save failed, try again] + error log · never a half-saved shelf (all or nothing) |

## Testing
- **Unit (pytest):** `parser` (every message form), `service` with `InMemoryRepo` (open, save, recount overwrite, summary, close, 10-minute expiry), `config` validation, `import_csv` with a sample CSV
- **Webhook:** FastAPI `TestClient` + a fake signature made with a test secret
- **Real smoke test:** run locally + ngrok → scan one real shelf QR from a phone

## Where it runs
- Dev: ณัฑฒ์'s machine + ngrok (LINE requires HTTPS)
- ❓ Production: not chosen yet (options: Render / Railway / Fly.io / Cloud Run) — it must answer the webhook before LINE times out; if a free tier sleeps and wakes slowly, use push messages instead of replies

## Phases 2–3 (direction only, not in this spec)
Photos in `shelf-photos` + confirmed counts → label in Roboflow → YOLO-seg → the bot pre-fills the counts and staff only reply `ok` or correct the numbers · start with SKUs that are clearly visible in photos (bottles/jars facing out, pouches standing in a row) before stacked items (books, pouches in baskets)

**Phase 3 — self-training:** new staff photos + staff-confirmed/corrected counts = new labels automatically → once enough accumulate → retrain → deploy the new model only if it beats the current one on the test set (never ship a worse model) · Phase 1 must always store the photo and the counts together so phase 3 is possible

## ❓ Open questions
- ✅ ~~Product codes on pages 2–3 were cropped~~ → the 28/9 sheet shows all 105 codes and is now the starting data, so there are no TEMP codes · foreign keys to `products.sku` still use `on update cascade` in case a code needs correcting
- ❓ Which products sit on which back-store shelf → ณัฑฒ์ walks the room and writes the layout into `config.yaml`
- ❓ Is the manager's permission needed before sticking QR codes on the shelves
- ❓ Is the LINE OA a new personal account of ณัฑฒ์'s or the company account
- ❓ Production host (see "Where it runs")
