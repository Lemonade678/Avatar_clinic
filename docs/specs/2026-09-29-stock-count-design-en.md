---
tags: [spec, code, avatar-clinic, computer-vision, english]
aliases: [Stock Count spec (EN, 29/9), Stock Count design English (29/9)]
status: done
status_note: "ฉบับเก่า — ใช้ 2026-09-30-stock-count-design-en แทน"
created: 2026-09-29
---
# 📦 Spec — Back-store stock counting (POC · MBK branch)

← [[Project - Stock Count]] · [[Code Hub - Avatar]] · 🇹🇭 ภาษาไทย: [[2026-09-29-stock-count-design]] · 🕘 previous: [[2026-09-28-stock-count-design-en]] · 🆕 ฉบับล่าสุด: [[2026-09-30-stock-count-design-en]]

## TL;DR
ณัฑฒ์ (the counter during the pilot) taps **Start** → walks to each back-store shelf and scans its QR → **a UI page pops up inside LINE** showing the products on that shelf, the expected (system) quantity and the last counted quantity → enters the real counts + takes a shelf photo → **a small CV model (Roboflow YOLO) counts from the photo to catch human error** → at the end of the shift taps **Submit** → counts land in Supabase + a summary of mismatches against the system + time taken → a weekly view shows which products move fastest.
A **minimap** (a floor plan of the back room, like a Siam Paragon mall directory) doubles as the SKU directory — search a product and see which shelf, left or right side, it lives on · designed so shelves/branches can be added later.

- **Pilot:** MBK (มาบุญครอง) branch back store · 1 month · counter = ณัฑฒ์
- **Phase 1 (this spec):** UI pages + minimap + time clock + counts and photos + small CV cross-check
- **Phase 2:** YOLO counting per SKU · **Phase 3:** the model retrains itself from incoming photos (separate specs)

## Goals / success criteria (over the 1-month pilot)
- Big goal: digital transformation of stock counting → present the pilot results to the company
- ✅ Back-store counting time per round **< 10 minutes** (the time clock measures every round · one timed paper round first as the baseline)
- ✅ Every counting day has a session covering every shelf in Supabase
- ✅ Mismatches against the system are visible right after submitting
- ✅ We can count how often CV caught a human error (⚠️ flags where a recount confirmed the human was wrong)
- ✅ A weekly fast-movers report exists
- ✅ Shelf photos paired with confirmed counts accumulate as the phase 2–3 dataset

## Scope
| In the POC | Out of the POC |
|---|---|
| MBK back store · one counter (ณัฑฒ์) | Front store, other branches, several counters at once |
| UI pages inside LINE (LIFF) rendered as HTML by FastAPI · minimap | A separate mobile app |
| One QR per shelf (left `L1…`, right `R1…`) | One QR per product |
| CV counts per **packaging type** (bottle/pouch/bag/box/book) | Per-SKU CV (phase 2), self-training (phase 3) |
| Starting stock from the 28/9/2026 sheet (CSV, 105 products) | Automatic link to the existing stock system (later: export → import) |
| Weekly fast-movers report (estimated from stock decreases) | Real sales figures from the POS |
| — | Typhoon OCR (dropped — the QR identifies the shelf) |

## Architecture
```
[QR on shelf L1] ──LINE camera──> https://liff.line.me/<LIFF_ID>?shelf=L1
                                        │ (opens inside LINE)
                                        ▼
                     [FastAPI (Python) — renders the HTML pages]
                       /map        minimap + Start / Submit shift buttons
                       /shelf/L1   products + expected + last count + inputs + photo
                       /report     weekly fast movers
                         │                     │                      │
                  identity via LINE       Roboflow API           Supabase
                  (LIFF ID token)        (count from photo)   (Postgres + Storage)
                                                                 │
                                          LINE Messaging API ── push the shift summary to ณัฑฒ์'s chat
```
- **Python 3.11+** · `fastapi` + `jinja2` (HTML pages) · `httpx` (LINE token verify / Roboflow) · `supabase` · `line-bot-sdk` v3 (push summary) · `pyyaml` · `qrcode[pil]` · `pytest`
- The only JavaScript is a short LIFF bootstrap (to obtain the user's ID token) — everything else is plain HTML/CSS with no framework (the minimap is a simple CSS grid, cheap to maintain long term)
- **UTF-8 everywhere:** code, templates and CSV files are UTF-8 · every page has `<meta charset="utf-8">` · responses are `text/html; charset=utf-8` · CSVs are read as `utf-8-sig` (accepts files saved by Excel)
- Human-edited config = `config.yaml` · secrets = `.env` (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_LIFF_CHANNEL_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ROBOFLOW_API_KEY`), never pushed to GitHub
- **No chat webhook any more** — all input goes through the UI pages · the LINE OA is only the entry point (rich menu → minimap) and receives the shift summary

## One round, step by step
1. Open the LINE OA → rich menu **"Back-room map"** → **minimap** page: left shelves `L1…` / right shelves `R1…` in their real order · grey = not counted · green = counted · orange = ⚠️ flag · a search box for SKU/name highlights the shelf holding it
2. Tap **⏱️ Start** → today's timer starts (if forgotten, it starts automatically when the first shelf is opened)
3. Scan the shelf QR (or tap the shelf on the minimap) → **shelf L1** page:

   | Product | System (expected) | Last count | Counted |
   |---|---|---|---|
   | อุระกาวาท | 10 | 10 (28/9) | [ input ] |
   | กัณฑรา | 5 | 5 (28/9) | [ input ] |

   + **📷 Shelf photo** button + **Save this shelf** button
4. Save → counts are stored for today's session (editable until the shift is submitted) → if there is a photo: send it to Roboflow → compare **totals per packaging type**, e.g. "bottle: CV 14 / entered 15" → difference above the tolerance = ⚠️ "please recount this shelf" · otherwise ✅
5. Back to the minimap → next shelf
6. Tap **📤 Submit shift** → timer stops → session closes → summary page: time taken · shelves not counted · products that differ from the system · CV flags → the same summary is pushed to ณัฑฒ์'s LINE chat
7. **/report** page → weekly fast movers

**The counter sees the system quantity** (no blind count) — for transparency, in line with the CEO's vision · it is also faster · trade-off discussed in [[R&D - Stock Count คู่แข่ง]]

## CV cross-check (small model)
- **Model:** a Roboflow object-detection project with classes `bottle`, `pouch`, `bag`, `box`, `book` · start with 50–100 hand-labelled back-room shelf photos · train on Roboflow (smallest size) · called through the Roboflow hosted API (no GPU needed)
- **Extra data:** every SKU has a `packaging` value (one of the 5 classes) in the product list
- **Comparison:** per shelf, per class → `human = sum of entered counts for SKUs of that class` · `cv = boxes the model finds (confidence ≥ threshold)` · ⚠️ flag when `|cv − human| > max(1, 10% of human)` (configurable in `config.yaml`)
- **No model yet / API down / no photo** → counts are saved normally with CV status "not checked" (CV is a helper, not a gate)
- ⚠️ Heavily stacked items (piles of books, pouches in baskets) will probably be under-counted → watch the pilot stats and switch CV off per shelf in `config.yaml`

## Data (Supabase)
| Table | Key columns | Notes |
|---|---|---|
| `products` | `sku` PK, `name`, `category`, `packaging` | from the CSV |
| `shelves` | `code` PK (`L1`, `R2`…), `label`, `side` (`L`/`R`), `position`, `cv_enabled` | from config.yaml |
| `shelf_products` | `shelf_code`, `sku`, `position` | display order |
| `stock_snapshots` | `sku`, `back_qty`, `as_of` | system (expected) stock · can import many days |
| `count_sessions` | `id`, `count_date` unique, `started_at`, `ended_at`, `line_user_id` | one per day · **time clock** = `ended_at − started_at` |
| `counts` | `session_id`, `shelf_code`, `sku`, `expected_qty`, `counted_qty`, `updated_at` | unique (session, sku) · a recount overwrites |
| `shelf_photos` | `session_id`, `shelf_code`, `storage_path`, `cv_counts` (jsonb), `human_counts` (jsonb), `cv_status` (`ok`/`flagged`/`skipped`) | images in the `shelf-photos` bucket = phase 2–3 dataset |

- `expected_qty` is copied from the snapshot at count time → historic reports stay correct
- "Last count" = the latest `counted_qty` of that SKU from an earlier session
- Only the LINE user ID is stored — no names or phone numbers · foreign keys to `products.sku` use `on update cascade` (codes can be corrected without breaking history)
- **Supabase ↔ GitHub:** a GitHub Action runs `supabase db push` on pushes to `main` (free plan)
- The schema already written (8 tables) changes through a **new migration**, never by editing the old one: add `packaging`, `side/position/cv_enabled`, `started_at/ended_at`, the CV columns · drop `user_state` (the UI knows the shelf from the URL)

## Weekly fast-movers report
- Stock that left, per SKU = sum of `max(0, previous count − this count)` across the week's sessions
- **Increases** are treated as restocks and not counted as sales
- ⚠️ This is an **estimate** — back-store stock also moves to the front store, not only out of the door → use it for trends ("what drains fastest"), not accounting
- `/report?week=2026-W40` shows the top 10 + a simple bar chart

## config.yaml (example)
```yaml
branch: mbk
line_basic_id: "@CHANGE-ME"      # LINE OA basic ID
liff_id: "CHANGE-ME"             # LIFF app ID (used to build QR links)
allowed_line_user_ids: []        # pilot: ณัฑฒ์'s LINE user ID
cv:
  model: "stock-count-packaging/1"   # Roboflow project/version
  min_confidence: 0.5
  tolerance_ratio: 0.10               # flag when off by more than max(1, 10%)
shelves:
  L1: { label: "ชั้นเหล็กซ้าย แถว 1", skus: [HB0001, HB0003, HB0004] }   # left steel shelf, row 1
  L2: { label: "ชั้นเหล็กซ้าย แถว 2", skus: [NA0025, NA0026] }
  R1: { label: "ตู้ขาวขวา ช่อง 1", skus: [NA0031, NA0032], cv_enabled: false }  # right white cabinet, slot 1
```
- The side (`L`/`R`) comes from the first letter of the shelf code · minimap order = file order
- The real layout is waiting for ณัฑฒ์'s walk-through

## Error handling
| Event | What happens |
|---|---|
| Page opened outside LINE / token fails | "Open through LINE only" page · HTTP 401 |
| User not on the allowlist | "No access" page · HTTP 403 · logged |
| Shelf not in the config | "Shelf X not found" + link back to the minimap · HTTP 404 |
| Empty / non-numeric / negative input | The form marks that field and saves nothing (whole shelf or nothing) · Thai digits ๐–๙ accepted |
| Today's shift already submitted | Shelf page becomes read-only and says so |
| Roboflow down / slower than 10 s | Counts saved normally · CV = "not checked" · logged |
| Supabase down | "Save failed, try again" · entered values stay in the form · logged |
| Pushing the summary to LINE fails | The session still closes · the summary page still works · logged |

## Testing
- **Unit (pytest):** CV comparison (`compare_cv`), weekly sales estimate, minimap layout from config, Thai digits, time clock (auto-start / stop / duration), config validation, CSV
- **Pages:** FastAPI `TestClient` + fake LINE verifier + fake Roboflow + `InMemoryRepo` → every page answers in UTF-8 and renders Thai correctly
- **Real smoke tests:** real Supabase (script cleans up its test data) · a real phone scanning one shelf QR through ngrok

## Where it runs
- Dev: ณัฑฒ์'s machine + ngrok (LIFF only opens HTTPS URLs)
- ❓ The 1-month pilot needs an always-on host (options: Render / Railway / Fly.io / Cloud Run) — ngrok only works while the computer is on

## Phases 2–3 (direction only)
- **Phase 2:** pilot photos + confirmed counts → per-product labels → YOLO-seg counting per SKU → the UI pre-fills counts and the counter only confirms
- **Phase 3 — self-training:** new photos + confirmed/corrected counts = new labels → once enough accumulate → retrain → switch only if the new model beats the old one on the test set

## ❓ Open questions
- ❓ The real MBK back-room layout (how many left/right shelves, what goes where) → ณัฑฒ์ walks the room
- ❓ `packaging` for the 105 SKUs → Claude drafts from category + photos, ณัฑฒ์ checks
- ✅ ~~The sheets say "สาขาลาดพร้าว" (Ladprao)~~ → confirmed by ณัฑฒ์ (30/9): this sheet is the **MBK** stock and is the pilot's starting stock · `config.yaml` now has `branch: mbk`
- ❓ Manager's permission before putting up QR codes · personal or company LINE OA
- ❓ Host for the 1-month pilot
