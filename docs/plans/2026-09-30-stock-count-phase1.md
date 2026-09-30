---
tags: [plan, code, avatar-clinic]
aliases: [Stock Count plan (30/9), แผนนับสต็อกเฟส 1 (30/9)]
status: done
status_note: "ทำครบ 9 task วันที่ 30/9 · เทสต์ 189 ผ่าน · ขั้นที่ต้องใช้บัญชีจริงอยู่ใน guide"
created: 2026-09-30
---
# Stock Count Phase 1 — Implementation Plan (30/9)

← [[Project - Stock Count]] · spec: [[2026-09-30-stock-count-design]] ([[2026-09-30-stock-count-design-en|EN]]) · 🕘 previous: [[2026-09-29-stock-count-phase1]]

> **For agentic workers:** execute task by task (superpowers:executing-plans), TDD, one commit per task. Each task starts with its **Objective** (🎯 EN / TH) as ณัฑฒ์ asked.

**Goal:** ณัฑฒ์ counts the MBK back store in under 10 minutes and under 20 taps: start the clock → open each slot (QR or minimap) → confirm/enter front-store quantities (typed, voice, or wrong-layout-proof) → optional photo cross-checked by a small CV model → submit → mismatch summary in LINE → weekly top 1–2–3 fast movers.

**Architecture:** FastAPI renders plain HTML pages (Jinja2) opened inside LINE through LIFF. Pure modules hold the rules (layout, minimap, CV comparison, weekly report, spoken-number parsing, keyboard repair); a `Repo` protocol hides storage (`InMemoryRepo` for tests/dev, `SupabaseRepo` for the pilot). Adapters wrap the outside world (LINE ID-token verify + push, Roboflow). Pilot runs on Railway (Singapore); data stays within 4 countries (TH, JP, SG, US).

**Tech stack:** Python 3.12 · FastAPI + Jinja2 + python-multipart + itsdangerous (signed session cookie) · httpx · supabase-py · line-bot-sdk v3 · Pillow · qrcode · jsQR (vendored JS) · pytest.

## Global constraints
- Expected quantity = latest `front_qty` (หน้าร้าน) · > 0 check · 0 skip · < 0 = system record wrong
- Layout comes from `data/layout_mbk.csv` (`sku,name,location,shelf,packaging`), slot code `<L|R><storey:02><position:02>`, x = `shelf`
- ≤ 20 taps per round · inputs pre-filled with the system value
- UTF-8 everywhere; every product name HTML-escaped; secrets only in `.env`
- Data within TH/JP/SG/US; no CDN at runtime (jsQR vendored)
- Transparency: the counter always sees the system quantity (CEO vision)
- Dev machine is **Windows** → every command below is given for PowerShell and Git Bash

## Commands (Windows)
| What | PowerShell | Git Bash |
|---|---|---|
| install | `python -m venv .venv; .venv\Scripts\python -m pip install -e ".[dev]"` | `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` |
| tests | `.venv\Scripts\python -m pytest -q` | `.venv/Scripts/python -m pytest -q` |
| run locally without LINE | `$env:APP_ENV="dev"; $env:DEV_USER_ID="U-dev"; .venv\Scripts\uvicorn stockcount.app:build_default_app --factory --reload` | `APP_ENV=dev DEV_USER_ID=U-dev .venv/Scripts/uvicorn stockcount.app:build_default_app --factory --reload` |
| minimap file | `.venv\Scripts\python scripts\make_minimap.py data\layout_mbk.csv data\stock_2026-09-28.csv` | `.venv/Scripts/python scripts/make_minimap.py data/layout_mbk.csv data/stock_2026-09-28.csv` |
| QR labels | `.venv\Scripts\python scripts\make_qr.py` | `.venv/Scripts/python scripts/make_qr.py` |

## Status 30/9 — all 9 tasks ✅
| Task | Result |
|---|---|
| 1 Config v2 | ✅ `config.py` (camera, CV, brightness, layout_file) |
| 2 Layout/seed/migration/import v2 | ✅ `packaging` column, `20260930000000_locations.sql`, import prints 4 tables |
| 3 Domain rules | ✅ `cv.py` `photo.py` `report.py` `speech.py` `thai_digits.py` |
| 4 Repo v2 | ✅ `InMemoryRepo.from_files` + `SupabaseRepo` + smoke script |
| 5 Counting service | ✅ clock, all-or-nothing save, photo+CV, next slot, submit+push, live minimap |
| 6 Web app | ✅ checked in the browser (dev mode, phone size) |
| 7 Adapters | ✅ Roboflow + LINE push, fail soft, keys never logged |
| 8 QR labels | ✅ real label decoded normal / mirrored / inverted / both |
| 9 Ship it | ✅ Procfile, railway.json, guides, to-dos, session log |

Not verified yet (needs ณัฑฒ์'s accounts): live Supabase, LINE LIFF login, Railway deploy, Roboflow endpoint, camera + speech inside LINE's in-app browser.

## Done before this plan (✅)
Scaffold + config loader · CSV loader with sum check · 105-product sheet · schema v1 + db-migrate Action · import script · slot codes + layout loader · keyboard-layout repair · static minimap page.

---

### Task 1 — Config v2
🎯 **EN:** config holds settings only (branch, LIFF, camera default, CV, allowlist); the shelf list moves to the layout CSV. **TH:** ให้ `config.yaml` เหลือแค่ค่าตั้ง ผังชั้นย้ายไปอยู่ใน CSV ที่ณัฑฒ์แก้เอง
- Files: `config.yaml`, `src/stockcount/config.py`, `tests/test_config.py`
- Tests: defaults when keys are missing · camera must be `back`/`front` · CV tolerance 0–1 · allowlist
- Done when: tests pass, old `shelves:` key no longer required

### Task 2 — Layout v2 (packaging) + seed v2 + migration v2 + import v2
🎯 **EN:** one editable CSV defines where every product sits and what packaging class the CV should see; the database mirrors it. **TH:** ไฟล์ผังไฟล์เดียวบอกทั้งตำแหน่งและประเภทบรรจุภัณฑ์ แล้ว import เข้า Supabase ได้ครบ
- Files: `data/layout_mbk.csv` (+`packaging`, Claude's guesses to review), `layout.py`, `seed.py`, `supabase/migrations/20260930000000_locations.sql`, `scripts/import_csv.py`, tests
- Tests: packaging must be one of bottle/pouch/bag/box/book or blank · seed builds `locations`, `product_locations`, snapshots with `front_qty` · migration parses
- Done when: tests pass; `import_csv.py` prints counts for all four tables

### Task 3 — Domain rules
🎯 **EN:** the maths behind the product, testable without any server: CV comparison, photo brightness, time clock, weekly report, spoken numbers. **TH:** กติกาทั้งหมดที่เป็นตรรกะล้วน เทสต์ได้โดยไม่ต้องมีเซิร์ฟเวอร์
- Files: `cv.py` (compare per packaging class, tolerance `max(1, 10%)`), `photo.py` (brightness 0–255, too-dark flag), `report.py` (top 1–2–3, weekly summary, CV match rate), `speech.py` (Thai/English number words + product matching, uses `keyboard.fix_layout`), tests
- Done when: all rule tests pass, including "อุระกาวาท เก้า ขวด" → HB0001 = 9 and "mala two" → MALA product = 2

### Task 4 — Repo v2
🎯 **EN:** one storage interface for sessions, counts, photos, layout and snapshots; in-memory for tests/dev, Supabase for the pilot. **TH:** ที่เก็บข้อมูลแบบเดียว ใช้ได้ทั้งตอนเทสต์และตอนใช้จริง
- Files: `repo.py` (Protocol + `InMemoryRepo.from_files(...)` + `SupabaseRepo`), `scripts/smoke_supabase.py`, tests
- Done when: in-memory tests pass; smoke script ready for ณัฑฒ์'s Supabase

### Task 5 — Counting service
🎯 **EN:** the flow of one round — start clock, open slot, save counts (all-or-nothing), attach photo + CV, submit shift, summary. **TH:** ลำดับการนับ 1 รอบ ตั้งแต่เริ่มจับเวลาจนส่งยอด
- Files: `service.py`, tests (Bangkok date, auto-start, read-only after submit, Thai digits, CV flagged/ok/skipped, summary numbers)
- Done when: service tests pass

### Task 6 — Web app
🎯 **EN:** the pages ณัฑฒ์ actually taps: `/map` (live minimap), `/loc/{code}`, `/scan`, `/summary`, `/report`; LIFF login in LINE, dev login on the PC. **TH:** หน้าจอที่ใช้จริงในมือถือ เปิดในแอป LINE และลองบนคอมได้โดยไม่ต้องมี LINE
- Files: `app.py`, `auth.py` (LIFF ID-token verify → signed cookie; `APP_ENV=dev` shortcut), `templates/*.html`, `static/` (app.css, scan.js, voice.js, vendored jsQR), tests with `TestClient`
- Done when: page tests pass and the app runs locally in dev mode (checked in the browser pane)

### Task 7 — Adapters
🎯 **EN:** talk to Roboflow and LINE without making them a hard dependency. **TH:** เชื่อม Roboflow และ LINE แบบที่ล่มได้โดยระบบหลักไม่ล่มตาม
- Files: `roboflow.py`, `line_push.py`, tests with fake HTTP
- Done when: timeouts/errors become "CV not checked" / "push failed" and never lose counts

### Task 8 — QR labels per slot
🎯 **EN:** one printable label per slot that opens that slot inside LINE. **TH:** ป้าย QR ต่อช่อง พิมพ์แปะได้เลย
- Files: `qr.py`, `scripts/make_qr.py`, tests (LIFF URL, mirrored/inverted readability is handled by the scanner page)

### Task 9 — Ship it
🎯 **EN:** everything ณัฑฒ์ needs to run the pilot: Railway start command, guides, to-dos, session log. **TH:** ของที่ต้องใช้ตอนขึ้นระบบจริง + คู่มือทีละขั้น
- Files: `Procfile`, `.env.example`, `Guides/guide-setup-stock-count-app.md`, vault notes
- Done when: full test suite passes, guide covers LINE LIFF + Railway + printing QR
