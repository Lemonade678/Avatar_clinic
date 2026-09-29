---
tags: [plan, code, avatar-clinic]
aliases: [Stock Count plan (29/9), แผนนับสต็อกเฟส 1 (29/9)]
status: draft
status_note: "ฉบับ 29/9 — มีคอมเมนต์ {} ของณัฑฒ์ รอปรับตาม design ใหม่"
created: 2026-09-29
---
# Stock Count Phase 1 Implementation Plan

← [[Project - Stock Count]] · [[2026-09-29-stock-count-design]] · 🇹🇭 ฉบับไทย: [[2026-09-29-stock-count-phase1-th]] · 🕘 ฉบับก่อน: [[2026-09-28-stock-count-phase1]]

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Back-store staff which is me scan a shelf QR type, counts into a LINE chat bot, and every count (plus an optional shelf photo that send to roboflow yolo model objection to tell how many it is so it just basic computer vision model {it also fact checking human error}) that lands in Supabase per day when shift done around , with a mismatch summary against the system stock. for mbk branch(pilot test) with time clock for checking session start. including digital minimap too like siam paragon minimap of shop aka sku directory. which susceptable for scaling in further

pilot duration 1 Month for phase 1

**Architecture:** A FastAPI webhook receives LINE events, verifies the signature, and hands text/images to a pure `StockService` (rules) that talks to a `Repo` interface. `SupabaseRepo` is the real store; `InMemoryRepo` backs the tests. The command `parser`, the reply `messages`, the `config` loader, the CSV loader and QR builder are small, pure modules. The schema lives in `supabase/migrations/` and a GitHub Action pushes it (Supabase free plan). 

**Tech Stack:** Python 3.12 (min 3.11) · FastAPI + uvicorn · line-bot-sdk v3 · supabase-py v2 · PyYAML · qrcode + Pillow ≥10.1 · python-dotenv · tzdata · pytest + httpx · Supabase CLI via `npx` (Node 24 is installed) · ngrok for local HTTPS. time for time counter and sustainable tech for minimap which like left and right side

**Status 2026-09-29:** Task 1 ✅, Task 2 ✅, schema + `db-migrate` Action + `scripts/import_csv.py` ✅ (pulled forward from Tasks 7–8). Next: Tasks 3–6, then `qr.py`/`make_qr.py` (Task 7) and `SupabaseRepo`/smoke script (Task 8).

**Spec:** `docs/specs/2026-09-28-stock-count-design.md` ([[2026-09-28-stock-count-design]])

## Global Constraints

- Repo root is `Avatar project/stock-count/` (already a git repo on branch `main`). All paths below are relative to it. Shell is Git Bash on Windows; the venv Python is `.venv/Scripts/python`.
- Python `>=3.11`; package lives in `src/stockcount/` (src layout).
- Human-edited config = `config.yaml`; secrets = `.env` (`LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`). `.env` is never committed.
- Code, identifiers, comments in English. Every user-facing bot string is Thai and lives only in `src/stockcount/messages.py`. {comment please ensure it have utp-8}
- Store only the LINE user ID of staff — no names, no phone numbers.
- A count session is one per **Asia/Bangkok** calendar date.
- An opened shelf stays active for **10 minutes** per user; saving counts restarts the window (so the photo prompt that follows has a full 10 minutes).
- Staff **see** the system quantity while counting (no blind count — ณัฑฒ์'s decision).{for transparency reason which align with ceo vision}
- Expected quantity = `back_qty` from the latest `stock_snapshots` row for that SKU (POC counts the back store only).
- Saving a shelf is all-or-nothing (one upsert statement); recounting a shelf overwrites the earlier numbers for that session.
- Supabase is on the **free plan** → migrations are applied by a GitHub Action running `supabase db push` on pushes to `main`.
- Product master = `data/stock_2026-09-28.csv` (105 real SKUs); every foreign key to `products.sku` uses `on update cascade` so a code can be corrected later without breaking history.
- Photos go to the private Supabase Storage bucket `shelf-photos`.
- LINE text replies are capped at 5,000 characters.

## Review Focus

1. **Thai-keyboard digits** — a staff member types `๗ ๘` instead of `7 8`; it must be read as 7 and 8 (test in Task 3). 
2. **Counting after midnight** — the server clock is UTC; a count at 01:30 Bangkok on 29/09 must go into the 29/09 session, not 28/09 (test in Task 5).
3. **CSV re-saved from Excel** — Excel adds a UTF-8 BOM; the loader must still find the `sku` column (test in Task 2).
4. **LINE reply fails** (expired reply token, redelivered event) — the webhook must still answer 200 so LINE does not retry forever, and the count must already be saved (test in Task 6).
5. **Correcting a product code after counts exist** — updating `products.sku` must carry through to counts/snapshots/shelf layout instead of failing (migration in Task 8, checked by the smoke script in Task 8).

## File Map

| File                                          | Responsibility                                                |
| --------------------------------------------- | ------------------------------------------------------------- |
| `pyproject.toml`                              | package + dependencies + pytest config                        |
| `config.yaml`                                 | branch, LINE basic ID, allowlist, shelf → SKU layout          |
| `.env.example`                                | names of the secrets                                          |
| `data/stock_2026-09-28.csv`                   | stock sheet transcribed from the 3 photographed pages         |
| `src/stockcount/config.py`                    | load + validate `config.yaml` → `AppConfig`                   |
| `src/stockcount/stock_csv.py`                 | read the CSV → `StockRow` list                                |
| `src/stockcount/seed.py`                      | config + rows → rows to insert (pure)                         |
| `src/stockcount/parser.py`                    | chat text → command object (pure)                             |
| `src/stockcount/repo.py`                      | `Repo` protocol, data classes, `InMemoryRepo`, `SupabaseRepo` |
| `src/stockcount/messages.py`                  | every Thai reply string                                       |
| `src/stockcount/service.py`                   | chat rules (`StockService`)                                   |
| `src/stockcount/app.py`                       | FastAPI webhook + production wiring                           |
| `src/stockcount/qr.py`                        | LINE deep link + printable QR label                           |
| `scripts/import_csv.py`                       | push CSV + layout into Supabase                               |
| `scripts/make_qr.py`                          | write one PNG label per shelf                                 |
| `scripts/smoke_supabase.py`                   | exercise `SupabaseRepo` against the real project              |
| `supabase/migrations/20260928000000_init.sql` | schema + bucket                                               |
| `.github/workflows/tests.yml`                 | run pytest on push                                            |
| `.github/workflows/db-migrate.yml`            | `supabase db push` on push to `main`                          |

---

### Task 1: Project scaffold + config loader
{please tell objective of the task in every task}
**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `config.yaml`, `src/stockcount/__init__.py`, `src/stockcount/config.py`, `.github/workflows/tests.yml`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class ConfigError(ValueError)`
  - `@dataclass(frozen=True) class Shelf: code: str; label: str; skus: tuple[str, ...]`
  - `@dataclass(frozen=True) class AppConfig: branch: str; line_basic_id: str; allowed_line_user_ids: frozenset[str]; shelves: dict[str, Shelf]` with method `is_allowed(user_id: str) -> bool`
  - `parse_config(raw: dict) -> AppConfig`, `load_config(path: str | Path) -> AppConfig`

- [ ] **Step 1: Write the scaffold files**

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "stockcount"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "line-bot-sdk>=3.11",
  "supabase>=2.4",
  "pyyaml>=6.0",
  "qrcode[pil]>=7.4",
  "pillow>=10.1",
  "python-dotenv>=1.0",
  "tzdata>=2024.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:
```
.env
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
out/
```

`.env.example`:
```
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ROBOFLOW_MODEL_API_KEY=
```

`config.yaml`:
```yaml
# ระบบนับสต็อกหลังร้าน — ไฟล์นี้แก้เองได้ (commit ขึ้น GitHub ได้ ไม่มีความลับ)
branch: mbk

# Basic ID ของ LINE OA (ขึ้นต้นด้วย @) — ดูใน LINE Official Account Manager
line_basic_id: "@CHANGE-ME"

# ว่าง = ใครแชทมาก็นับได้ (ช่วงทดลอง) · ใส่ LINE user ID = จำกัดเฉพาะคนในลิสต์
allowed_line_user_ids: []

# ผังชั้นหลังร้าน: รหัสชั้น → สินค้าตามลำดับที่ bot จะแสดง
#  ตัวอย่าง 3 ชั้น ทั้งฝั่งซ้ายและขวา
shelves:
  L1:
    label: "ชั้นเหล็กซ้าย แถว 1"
    skus: [HB0001, HB0003, HB0004]
  L2:
    label: "ชั้นเหล็กซ้าย แถว 2"
    skus: [NA0025, NA0026]
  L3:
	label: "ชั้นเหล็กซ้าย แถว 3"
	skus : [G]  
```

`src/stockcount/__init__.py`:
```python
"""Back-store stock counting over LINE."""
```

`.github/workflows/tests.yml`:
```yaml
name: tests
on: [push, pull_request]
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest -q
```

- [ ] **Step 2: Create the venv and install**

Run: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`
Expected: ends with `Successfully installed ... stockcount-0.1.0 ...`

- [ ] **Step 3: Write the failing test** — `tests/test_config.py`

```python
from pathlib import Path

import pytest

from stockcount.config import ConfigError, load_config, parse_config


def raw(**over):
    base = {
        "branch": "ladprao",
        "line_basic_id": "@abc1234",
        "shelves": {"A1": {"label": "ชั้นเหล็กซ้าย 1", "skus": ["HB0001", "HB0003"]}},
    }
    base.update(over)
    return base


def test_parses_shelf_label_and_sku_order():
    cfg = parse_config(raw())
    assert cfg.shelves["A1"].label == "ชั้นเหล็กซ้าย 1"
    assert cfg.shelves["A1"].skus == ("HB0001", "HB0003")


def test_lowercase_shelf_code_is_uppercased():
    cfg = parse_config(raw(shelves={"a1": {"skus": ["X1"]}}))
    assert "A1" in cfg.shelves


def test_label_defaults_to_code():
    cfg = parse_config(raw(shelves={"B2": {"skus": ["X1"]}}))
    assert cfg.shelves["B2"].label == "B2"


def test_sku_on_two_shelves_is_rejected():
    with pytest.raises(ConfigError, match="HB0001"):
        parse_config(raw(shelves={"A1": {"skus": ["HB0001"]}, "A2": {"skus": ["HB0001"]}}))


def test_shelf_without_skus_is_rejected():
    with pytest.raises(ConfigError, match="A1"):
        parse_config(raw(shelves={"A1": {"skus": []}}))


def test_bad_shelf_code_is_rejected():
    with pytest.raises(ConfigError, match="bad shelf code"):
        parse_config(raw(shelves={"ชั้น1": {"skus": ["X1"]}}))


def test_missing_basic_id_is_rejected():
    bad = raw()
    del bad["line_basic_id"]
    with pytest.raises(ConfigError, match="line_basic_id"):
        parse_config(bad)


def test_empty_allowlist_allows_everyone():
    assert parse_config(raw()).is_allowed("U-anyone")


def test_allowlist_blocks_others():
    cfg = parse_config(raw(allowed_line_user_ids=["U-ok"]))
    assert cfg.is_allowed("U-ok")
    assert not cfg.is_allowed("U-other")


def test_repo_config_yaml_loads():
    cfg = load_config(Path(__file__).parents[1] / "config.yaml")
    assert cfg.branch == "ladprao"
    assert list(cfg.shelves) == ["A1", "A2"]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stockcount.config'`

- [ ] **Step 5: Implement** — `src/stockcount/config.py`

```python
"""Load and validate config.yaml: branch, LINE basic ID, allowlist, shelf layout."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SHELF_CODE_RE = re.compile(r"^[A-Z0-9-]{1,10}$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Shelf:
    code: str
    label: str
    skus: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    branch: str
    line_basic_id: str
    allowed_line_user_ids: frozenset[str]
    shelves: dict[str, Shelf]

    def is_allowed(self, user_id: str) -> bool:
        return not self.allowed_line_user_ids or user_id in self.allowed_line_user_ids


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_config(raw)


def parse_config(raw: dict) -> AppConfig:
    for key in ("branch", "line_basic_id", "shelves"):
        if not raw.get(key):
            raise ConfigError(f"missing '{key}'")

    shelves: dict[str, Shelf] = {}
    shelf_of_sku: dict[str, str] = {}
    for code, body in raw["shelves"].items():
        code = str(code).upper()
        if not SHELF_CODE_RE.match(code):
            raise ConfigError(f"bad shelf code '{code}' (use A-Z, 0-9, -)")
        body = body or {}
        skus = tuple(str(s) for s in body.get("skus") or ())
        if not skus:
            raise ConfigError(f"shelf {code} has no skus")
        for sku in skus:
            if sku in shelf_of_sku:
                raise ConfigError(f"sku {sku} is on both {shelf_of_sku[sku]} and {code}")
            shelf_of_sku[sku] = code
        shelves[code] = Shelf(code=code, label=str(body.get("label", code)), skus=skus)

    return AppConfig(
        branch=str(raw["branch"]),
        line_basic_id=str(raw["line_basic_id"]),
        allowed_line_user_ids=frozenset(raw.get("allowed_line_user_ids") or ()),
        shelves=shelves,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: 10 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example config.yaml src tests .github/workflows/tests.yml
git commit -m "feat: project scaffold and config.yaml loader"
```

---

### Task 2: Stock sheet CSV + loader + seed builder — ✅ DONE 2026-09-29

Built from the **28/9/2026** sheet, which shows every product code, so there are no `TEMP-*` codes and no `code_hint` column.

- `data/stock_2026-09-28.csv` — 105 rows, columns `sku,name,category,back_qty,front_qty,system_qty,needs_review` (`needs_review=true` only for HB0083 and NA0031, whose printed names are hard to read / truncated)
- `src/stockcount/stock_csv.py` — `StockRow(sku, name, category, back_qty, front_qty, system_qty, needs_review)`, `load_stock_csv(path)`, `StockCsvError`; also rejects a row whose `system_qty != back_qty + front_qty` (all 105 rows pass — a check on the transcription)
- `src/stockcount/seed.py` — `SeedData`, `build_seed(config, rows, as_of)`, `SeedError`
- Tests: `tests/test_stock_csv.py` (8), `tests/test_seed.py` (3)

---

### Task 3: Chat command parser

**Files:**
- Create: `src/stockcount/parser.py`
- Test: `tests/test_parser.py`

**Interfaces:**
- Consumes: nothing
- Produces: frozen dataclasses `OpenShelf(code: str)`, `Counts(values: tuple[int, ...])`, `Skip()`, `Summary()`, `CloseSession()`, `NegativeCount()`, `Unknown()`; type alias `Command`; `parse(text: str) -> Command`

- [ ] **Step 1: Write the failing test** — `tests/test_parser.py`

```python
import pytest

from stockcount.parser import (
    CloseSession,
    Counts,
    NegativeCount,
    OpenShelf,
    Skip,
    Summary,
    Unknown,
    parse,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ชั้น A2", OpenShelf("A2")),
        ("ชั้นa2", OpenShelf("A2")),
        ("  ชั้น  B-10 ", OpenShelf("B-10")),
        ("7 8", Counts((7, 8))),
        ("7,8", Counts((7, 8))),
        ("7\n8\n0", Counts((7, 8, 0))),
        ("12", Counts((12,))),
        ("๗ ๘", Counts((7, 8))),  # Thai-keyboard digits
        ("ข้าม", Skip()),
        ("สรุป", Summary()),
        ("ปิดรอบ", CloseSession()),
        ("7 -1", NegativeCount()),
        ("สวัสดี", Unknown()),
        ("", Unknown()),
        ("7 แปด", Unknown()),
    ],
)
def test_parse(text, expected):
    assert parse(text) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stockcount.parser'`

- [ ] **Step 3: Implement** — `src/stockcount/parser.py`

```python
"""Turn a LINE chat message into a command. Pure: no I/O."""
from __future__ import annotations

import re
from dataclasses import dataclass

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
SHELF_RE = re.compile(r"^ชั้น\s*([A-Za-z0-9-]{1,10})$")
NUMBER_RE = re.compile(r"^-?\d+$")
SEPARATOR_RE = re.compile(r"[\s,]+")


@dataclass(frozen=True)
class OpenShelf:
    code: str


@dataclass(frozen=True)
class Counts:
    values: tuple[int, ...]


@dataclass(frozen=True)
class Skip:
    pass


@dataclass(frozen=True)
class Summary:
    pass


@dataclass(frozen=True)
class CloseSession:
    pass


@dataclass(frozen=True)
class NegativeCount:
    pass


@dataclass(frozen=True)
class Unknown:
    pass


Command = OpenShelf | Counts | Skip | Summary | CloseSession | NegativeCount | Unknown

KEYWORDS: dict[str, Command] = {"ข้าม": Skip(), "สรุป": Summary(), "ปิดรอบ": CloseSession()}


def parse(text: str) -> Command:
    cleaned = text.translate(THAI_DIGITS).strip()
    if cleaned in KEYWORDS:
        return KEYWORDS[cleaned]

    shelf = SHELF_RE.match(cleaned)
    if shelf:
        return OpenShelf(shelf.group(1).upper())

    tokens = [t for t in SEPARATOR_RE.split(cleaned) if t]
    if tokens and all(NUMBER_RE.match(t) for t in tokens):
        values = tuple(int(t) for t in tokens)
        return NegativeCount() if any(v < 0 for v in values) else Counts(values)

    return Unknown()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_parser.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add src/stockcount/parser.py tests/test_parser.py
git commit -m "feat: chat command parser (Thai digits, comma/newline separators)"
```

---

### Task 4: Repo interface + in-memory repo

**Files:**
- Create: `src/stockcount/repo.py`
- Test: `tests/test_repo_memory.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `@dataclass(frozen=True) class Session: id: str; count_date: date; closed: bool`
  - `@dataclass(frozen=True) class CountRow: shelf_code: str; sku: str; expected_qty: int; counted_qty: int`
  - `@dataclass(frozen=True) class UserState: shelf_code: str; opened_at: datetime`
  - `class Repo(Protocol)` with:
    - `get_or_open_session(count_date: date, now: datetime) -> Session`
    - `close_session(session_id: str, now: datetime) -> None`
    - `product_names(skus: list[str]) -> dict[str, str]`
    - `expected_back_qty(skus: list[str]) -> dict[str, int]`
    - `save_counts(session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None`
    - `list_counts(session_id: str) -> list[CountRow]`
    - `get_user_state(user_id: str) -> UserState | None`
    - `set_user_state(user_id: str, shelf_code: str, now: datetime) -> None`
    - `save_photo(session_id: str, shelf_code: str, user_id: str, content: bytes, now: datetime) -> str`
  - `class InMemoryRepo(names: dict[str, str] | None = None, expected: dict[str, int] | None = None)` implementing `Repo`; session ids are `f"s-{count_date.isoformat()}"`; exposes `sessions`, `photos` for tests
  - (`SupabaseRepo` is added to this same file in Task 8)

- [ ] **Step 1: Write the failing test** — `tests/test_repo_memory.py`

```python
from datetime import date, datetime, timezone

from stockcount.repo import CountRow, InMemoryRepo

NOW = datetime(2026, 9, 28, 3, 0, tzinfo=timezone.utc)
DAY = date(2026, 9, 28)


def test_one_session_per_date():
    repo = InMemoryRepo()
    a = repo.get_or_open_session(DAY, NOW)
    b = repo.get_or_open_session(DAY, NOW)
    c = repo.get_or_open_session(date(2026, 9, 29), NOW)
    assert a.id == b.id == "s-2026-09-28"
    assert c.id != a.id


def test_close_session():
    repo = InMemoryRepo()
    s = repo.get_or_open_session(DAY, NOW)
    repo.close_session(s.id, NOW)
    assert repo.get_or_open_session(DAY, NOW).closed


def test_save_counts_overwrites_same_sku():
    repo = InMemoryRepo()
    repo.save_counts("s1", [CountRow("A1", "X", 5, 3)], "U1", NOW)
    repo.save_counts("s1", [CountRow("A1", "X", 5, 5)], "U1", NOW)
    assert repo.list_counts("s1") == [CountRow("A1", "X", 5, 5)]


def test_lookups_skip_unknown_skus():
    repo = InMemoryRepo(names={"X": "ex"}, expected={"X": 4})
    assert repo.product_names(["X", "Y"]) == {"X": "ex"}
    assert repo.expected_back_qty(["X", "Y"]) == {"X": 4}


def test_user_state_round_trip():
    repo = InMemoryRepo()
    assert repo.get_user_state("U1") is None
    repo.set_user_state("U1", "A1", NOW)
    state = repo.get_user_state("U1")
    assert (state.shelf_code, state.opened_at) == ("A1", NOW)


def test_save_photo_returns_path():
    repo = InMemoryRepo()
    path = repo.save_photo("s1", "A1", "U1", b"jpg", NOW)
    assert path.startswith("s1/A1/")
    assert repo.photos[0]["shelf_code"] == "A1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_repo_memory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stockcount.repo'`

- [ ] **Step 3: Implement** — `src/stockcount/repo.py`

```python
"""Data access. InMemoryRepo backs tests; SupabaseRepo (below) is the real store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class Session:
    id: str
    count_date: date
    closed: bool


@dataclass(frozen=True)
class CountRow:
    shelf_code: str
    sku: str
    expected_qty: int
    counted_qty: int


@dataclass(frozen=True)
class UserState:
    shelf_code: str
    opened_at: datetime


class Repo(Protocol):
    def get_or_open_session(self, count_date: date, now: datetime) -> Session: ...
    def close_session(self, session_id: str, now: datetime) -> None: ...
    def product_names(self, skus: list[str]) -> dict[str, str]: ...
    def expected_back_qty(self, skus: list[str]) -> dict[str, int]: ...
    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None: ...
    def list_counts(self, session_id: str) -> list[CountRow]: ...
    def get_user_state(self, user_id: str) -> UserState | None: ...
    def set_user_state(self, user_id: str, shelf_code: str, now: datetime) -> None: ...
    def save_photo(self, session_id: str, shelf_code: str, user_id: str, content: bytes, now: datetime) -> str: ...


class InMemoryRepo:
    def __init__(self, names: dict[str, str] | None = None, expected: dict[str, int] | None = None):
        self.names = dict(names or {})
        self.expected = dict(expected or {})
        self.sessions: dict[date, dict] = {}
        self.counts: dict[tuple[str, str], CountRow] = {}
        self.states: dict[str, UserState] = {}
        self.photos: list[dict] = []

    def get_or_open_session(self, count_date: date, now: datetime) -> Session:
        s = self.sessions.setdefault(count_date, {"id": f"s-{count_date.isoformat()}", "closed_at": None})
        return Session(id=s["id"], count_date=count_date, closed=s["closed_at"] is not None)

    def close_session(self, session_id: str, now: datetime) -> None:
        for s in self.sessions.values():
            if s["id"] == session_id:
                s["closed_at"] = now

    def product_names(self, skus: list[str]) -> dict[str, str]:
        return {s: self.names[s] for s in skus if s in self.names}

    def expected_back_qty(self, skus: list[str]) -> dict[str, int]:
        return {s: self.expected[s] for s in skus if s in self.expected}

    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None:
        for row in rows:
            self.counts[(session_id, row.sku)] = row

    def list_counts(self, session_id: str) -> list[CountRow]:
        return [row for (sid, _), row in self.counts.items() if sid == session_id]

    def get_user_state(self, user_id: str) -> UserState | None:
        return self.states.get(user_id)

    def set_user_state(self, user_id: str, shelf_code: str, now: datetime) -> None:
        self.states[user_id] = UserState(shelf_code=shelf_code, opened_at=now)

    def save_photo(self, session_id: str, shelf_code: str, user_id: str, content: bytes, now: datetime) -> str:
        path = f"{session_id}/{shelf_code}/{len(self.photos) + 1}.jpg"
        self.photos.append({"session_id": session_id, "shelf_code": shelf_code, "user_id": user_id, "path": path})
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_repo_memory.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/stockcount/repo.py tests/test_repo_memory.py
git commit -m "feat: repo interface and in-memory implementation"
```

---

### Task 5: Reply messages + StockService rules

**Files:**
- Create: `src/stockcount/messages.py`, `src/stockcount/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: `AppConfig`, `Shelf`, `parse_config` (Task 1); `parse` + command classes (Task 3); `Repo`, `CountRow`, `InMemoryRepo` (Task 4)
- Produces:
  - `messages`: constants `SCAN_FIRST`, `SESSION_CLOSED`, `SAVE_FAILED`, `NEGATIVE`, `SKIPPED`, `HELP`; functions `unknown_shelf(code) -> str`, `shelf_list(shelf, names, expected, count_date) -> str`, `wrong_count(n, example) -> str`, `saved(shelf_code, mismatches) -> str`, `photo_saved(shelf_code) -> str`, `summary(done, missing, mismatches, closed) -> str` where `mismatches: list[tuple[str, int, int]]` = (name, expected, counted)
  - `service`: `BANGKOK: ZoneInfo`, `STATE_TTL = timedelta(minutes=10)`, `class StockService(config: AppConfig, repo: Repo, clock: Callable[[], datetime])` with `handle_text(user_id: str, text: str) -> str | None` and `handle_image(user_id: str, content: bytes) -> str | None` (`None` = do not reply)

- [ ] **Step 1: Write the failing test** — `tests/test_service.py`

```python
from datetime import date, datetime, timedelta, timezone

import pytest

from stockcount import messages as msg
from stockcount.config import parse_config
from stockcount.repo import InMemoryRepo
from stockcount.service import StockService

UTC = timezone.utc
RAW = {
    "branch": "ladprao",
    "line_basic_id": "@abc",
    "shelves": {
        "A1": {"label": "ซ้าย 1", "skus": ["HB0001", "HB0003"]},
        "A2": {"label": "ซ้าย 2", "skus": ["NA0025"]},
    },
}
NAMES = {"HB0001": "อระกาวาท", "HB0003": "กัณฑรา", "NA0025": "ROZY Bag (15g.)"}
EXPECTED = {"HB0001": 10, "HB0003": 5, "NA0025": 0}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


@pytest.fixture
def env():
    repo = InMemoryRepo(NAMES, EXPECTED)
    clock = Clock(datetime(2026, 9, 28, 3, 0, tzinfo=UTC))  # 10:00 in Bangkok
    return StockService(parse_config(RAW), repo, clock), repo, clock


def test_open_shelf_lists_items_with_system_qty(env):
    svc, _, _ = env
    reply = svc.handle_text("U1", "ชั้น A1")
    assert "ชั้น A1 (ซ้าย 1) — 28/09" in reply
    assert "1. อระกาวาท  ระบบ 10" in reply
    assert "2. กัณฑรา  ระบบ 5" in reply


def test_unknown_shelf(env):
    svc, _, _ = env
    assert svc.handle_text("U1", "ชั้น Z9") == msg.unknown_shelf("Z9")


def test_counts_before_scanning(env):
    svc, _, _ = env
    assert svc.handle_text("U1", "7 8") == msg.SCAN_FIRST


def test_save_counts_reports_only_mismatches(env):
    svc, repo, _ = env
    svc.handle_text("U1", "ชั้น A1")
    reply = svc.handle_text("U1", "10 3")
    assert "✅ ชั้น A1 บันทึกแล้ว" in reply
    assert "• กัณฑรา (ระบบ 5 / นับ 3)" in reply
    assert "อระกาวาท" not in reply
    rows = repo.list_counts("s-2026-09-28")
    assert {(r.sku, r.expected_qty, r.counted_qty) for r in rows} == {("HB0001", 10, 10), ("HB0003", 5, 3)}


def test_all_match_message(env):
    svc, _, _ = env
    svc.handle_text("U1", "ชั้น A1")
    assert "ตรงกับระบบทุกรายการ" in svc.handle_text("U1", "10 5")


def test_wrong_number_of_counts_saves_nothing(env):
    svc, repo, _ = env
    svc.handle_text("U1", "ชั้น A1")
    assert svc.handle_text("U1", "10") == msg.wrong_count(2, "10 5")
    assert repo.list_counts("s-2026-09-28") == []


def test_recount_overwrites(env):
    svc, repo, _ = env
    svc.handle_text("U1", "ชั้น A1")
    svc.handle_text("U1", "10 3")
    svc.handle_text("U1", "10 5")
    rows = {r.sku: r.counted_qty for r in repo.list_counts("s-2026-09-28")}
    assert rows == {"HB0001": 10, "HB0003": 5}


def test_open_shelf_expires_after_10_minutes(env):
    svc, _, clock = env
    svc.handle_text("U1", "ชั้น A1")
    clock.advance(minutes=11)
    assert svc.handle_text("U1", "10 5") == msg.SCAN_FIRST


def test_session_uses_bangkok_date(env):
    svc, repo, clock = env
    clock.t = datetime(2026, 9, 28, 18, 30, tzinfo=UTC)  # 01:30 on 29/09 in Bangkok
    assert "— 29/09" in svc.handle_text("U1", "ชั้น A1")
    assert date(2026, 9, 29) in repo.sessions


def test_photo_attaches_to_open_shelf(env):
    svc, repo, _ = env
    svc.handle_text("U1", "ชั้น A1")
    svc.handle_text("U1", "10 5")
    assert svc.handle_image("U1", b"jpg") == msg.photo_saved("A1")
    assert repo.photos[0]["shelf_code"] == "A1"


def test_photo_without_open_shelf_is_rejected(env):
    svc, repo, _ = env
    assert svc.handle_image("U1", b"jpg") == msg.SCAN_FIRST
    assert repo.photos == []


def test_saving_counts_restarts_photo_window(env):
    svc, repo, clock = env
    svc.handle_text("U1", "ชั้น A1")
    clock.advance(minutes=8)
    svc.handle_text("U1", "10 5")
    clock.advance(minutes=8)  # 16 min after opening, 8 after saving
    assert svc.handle_image("U1", b"jpg") == msg.photo_saved("A1")


def test_skip(env):
    svc, _, _ = env
    assert svc.handle_text("U1", "ข้าม") == msg.SKIPPED


def test_summary_lists_missing_shelves_and_mismatches(env):
    svc, _, _ = env
    svc.handle_text("U1", "ชั้น A1")
    svc.handle_text("U1", "10 3")
    reply = svc.handle_text("U1", "สรุป")
    assert "📋 นับแล้ว 1/2 ชั้น" in reply
    assert "ยังไม่นับ: A2" in reply
    assert "• กัณฑรา (ระบบ 5 / นับ 3)" in reply


def test_close_session_blocks_more_counting_today(env):
    svc, _, _ = env
    assert "🔒 ปิดรอบแล้ว" in svc.handle_text("U1", "ปิดรอบ")
    assert svc.handle_text("U1", "ชั้น A1") == msg.SESSION_CLOSED


def test_next_day_opens_a_new_session(env):
    svc, _, clock = env
    svc.handle_text("U1", "ปิดรอบ")
    clock.advance(days=1)
    assert "— 29/09" in svc.handle_text("U1", "ชั้น A1")


def test_negative_and_unknown_text(env):
    svc, _, _ = env
    assert svc.handle_text("U1", "-3") == msg.NEGATIVE
    assert svc.handle_text("U1", "สวัสดี") == msg.HELP


def test_user_outside_allowlist_gets_no_reply():
    cfg = parse_config({**RAW, "allowed_line_user_ids": ["U-ok"]})
    svc = StockService(cfg, InMemoryRepo(NAMES, EXPECTED), lambda: datetime(2026, 9, 28, tzinfo=UTC))
    assert svc.handle_text("U-other", "ชั้น A1") is None
    assert svc.handle_image("U-other", b"jpg") is None


def test_repo_failure_returns_save_failed(env, monkeypatch):
    svc, repo, _ = env
    svc.handle_text("U1", "ชั้น A1")

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(repo, "save_counts", boom)
    assert svc.handle_text("U1", "10 5") == msg.SAVE_FAILED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'messages' from 'stockcount'`

- [ ] **Step 3: Implement**

`src/stockcount/messages.py`:
```python
"""Every Thai reply the bot sends. Keep user-facing text here and nowhere else."""
from __future__ import annotations

from datetime import date

from .config import Shelf

SCAN_FIRST = "สแกน QR ที่ชั้นก่อนนะครับ"
SESSION_CLOSED = "รอบนับวันนี้ปิดแล้วครับ"
SAVE_FAILED = "บันทึกไม่สำเร็จ ลองอีกครั้งนะครับ"
NEGATIVE = "ยอดติดลบไม่ได้ครับ ถ้าไม่มีของให้พิมพ์ 0"
SKIPPED = "ข้ามรูปแล้วครับ สแกนชั้นถัดไปได้เลย"
HELP = 'สแกน QR ที่ชั้นเพื่อเริ่มนับ · พิมพ์ "สรุป" ดูภาพรวม · พิมพ์ "ปิดรอบ" เมื่อนับครบ'

Mismatch = tuple[str, int, int]  # (product name, expected, counted)


def unknown_shelf(code: str) -> str:
    return f"ไม่พบชั้น {code} — ลองสแกน QR ใหม่ครับ"


def shelf_list(shelf: Shelf, names: dict[str, str], expected: dict[str, int], count_date: date) -> str:
    lines = [f"ชั้น {shelf.code} ({shelf.label}) — {count_date:%d/%m}"]
    for i, sku in enumerate(shelf.skus, start=1):
        lines.append(f"{i}. {names.get(sku, sku)}  ระบบ {expected.get(sku, 0)}")
    example = " ".join(str(expected.get(sku, 0)) for sku in shelf.skus)
    lines.append(f"พิมพ์ยอดตามลำดับ เว้นวรรค เช่น: {example}")
    return "\n".join(lines)


def wrong_count(n: int, example: str) -> str:
    return f"ชั้นนี้มี {n} รายการ ต้องพิมพ์ {n} ตัวเลข เช่น: {example}"


def _mismatch_lines(mismatches: list[Mismatch]) -> list[str]:
    return [f"• {name} (ระบบ {exp} / นับ {got})" for name, exp, got in mismatches]


def saved(shelf_code: str, mismatches: list[Mismatch]) -> str:
    lines = [f"✅ ชั้น {shelf_code} บันทึกแล้ว"]
    if mismatches:
        lines.append("ไม่ตรงกับระบบ:")
        lines += _mismatch_lines(mismatches)
    else:
        lines.append("ตรงกับระบบทุกรายการ")
    lines.append('ถ่ายรูปชั้นส่งมา 1 รูป (หรือพิมพ์ "ข้าม")')
    return "\n".join(lines)


def photo_saved(shelf_code: str) -> str:
    return f"📷 ได้รูปชั้น {shelf_code} แล้วครับ"


def summary(done: list[str], missing: list[str], mismatches: list[Mismatch], closed: bool) -> str:
    head = "🔒 ปิดรอบแล้ว — " if closed else "📋 "
    lines = [f"{head}นับแล้ว {len(done)}/{len(done) + len(missing)} ชั้น"]
    if missing:
        lines.append("ยังไม่นับ: " + ", ".join(missing))
    if mismatches:
        lines.append(f"ไม่ตรงกับระบบ {len(mismatches)} รายการ:")
        lines += _mismatch_lines(mismatches)
    else:
        lines.append("ยังไม่มีรายการที่ไม่ตรง")
    return "\n".join(lines)
```

`src/stockcount/service.py`:
```python
"""Chat rules: open a shelf, save counts, attach photos, summarise, close the day."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from . import messages as msg
from .config import AppConfig
from .parser import CloseSession, Command, Counts, NegativeCount, OpenShelf, Skip, Summary, parse
from .repo import CountRow, Repo, Session

BANGKOK = ZoneInfo("Asia/Bangkok")
STATE_TTL = timedelta(minutes=10)

log = logging.getLogger(__name__)


class StockService:
    def __init__(self, config: AppConfig, repo: Repo, clock: Callable[[], datetime]):
        self.config = config
        self.repo = repo
        self.clock = clock

    def handle_text(self, user_id: str, text: str) -> str | None:
        if not self.config.is_allowed(user_id):
            log.warning("ignored message from user outside allowlist: %s", user_id)
            return None
        try:
            return self._dispatch(user_id, parse(text))
        except Exception:
            log.exception("handle_text failed")
            return msg.SAVE_FAILED

    def handle_image(self, user_id: str, content: bytes) -> str | None:
        if not self.config.is_allowed(user_id):
            log.warning("ignored image from user outside allowlist: %s", user_id)
            return None
        try:
            now = self.clock()
            code = self._active_shelf(user_id, now)
            if code is None:
                return msg.SCAN_FIRST
            session = self._session(now)
            if session.closed:
                return msg.SESSION_CLOSED
            self.repo.save_photo(session.id, code, user_id, content, now)
            return msg.photo_saved(code)
        except Exception:
            log.exception("handle_image failed")
            return msg.SAVE_FAILED

    def _dispatch(self, user_id: str, command: Command) -> str:
        now = self.clock()
        match command:
            case OpenShelf(code):
                return self._open(user_id, code, now)
            case Counts(values):
                return self._save(user_id, values, now)
            case Skip():
                return msg.SKIPPED
            case Summary():
                return self._summary(now, close=False)
            case CloseSession():
                return self._summary(now, close=True)
            case NegativeCount():
                return msg.NEGATIVE
            case _:
                return msg.HELP

    def _session(self, now: datetime) -> Session:
        return self.repo.get_or_open_session(now.astimezone(BANGKOK).date(), now)

    def _active_shelf(self, user_id: str, now: datetime) -> str | None:
        state = self.repo.get_user_state(user_id)
        if state is None or now - state.opened_at > STATE_TTL:
            return None
        return state.shelf_code

    def _open(self, user_id: str, code: str, now: datetime) -> str:
        shelf = self.config.shelves.get(code)
        if shelf is None:
            return msg.unknown_shelf(code)
        session = self._session(now)
        if session.closed:
            return msg.SESSION_CLOSED
        self.repo.set_user_state(user_id, shelf.code, now)
        skus = list(shelf.skus)
        return msg.shelf_list(shelf, self.repo.product_names(skus), self.repo.expected_back_qty(skus), session.count_date)

    def _save(self, user_id: str, values: tuple[int, ...], now: datetime) -> str:
        code = self._active_shelf(user_id, now)
        shelf = self.config.shelves.get(code) if code else None
        if shelf is None:
            return msg.SCAN_FIRST
        session = self._session(now)
        if session.closed:
            return msg.SESSION_CLOSED

        skus = list(shelf.skus)
        expected = self.repo.expected_back_qty(skus)
        if len(values) != len(skus):
            return msg.wrong_count(len(skus), " ".join(str(expected.get(s, 0)) for s in skus))

        rows = [CountRow(shelf.code, sku, expected.get(sku, 0), value) for sku, value in zip(skus, values)]
        self.repo.save_counts(session.id, rows, user_id, now)
        self.repo.set_user_state(user_id, shelf.code, now)  # restart the window for the photo prompt
        return msg.saved(shelf.code, self._mismatches(rows, self.repo.product_names(skus)))

    def _summary(self, now: datetime, close: bool) -> str:
        session = self._session(now)
        if close and not session.closed:
            self.repo.close_session(session.id, now)
        rows = sorted(self.repo.list_counts(session.id), key=lambda r: (r.shelf_code, r.sku))
        counted = {r.shelf_code for r in rows}
        done = [c for c in self.config.shelves if c in counted]
        missing = [c for c in self.config.shelves if c not in counted]
        names = self.repo.product_names([r.sku for r in rows])
        return msg.summary(done, missing, self._mismatches(rows, names), closed=close or session.closed)

    @staticmethod
    def _mismatches(rows: list[CountRow], names: dict[str, str]) -> list[msg.Mismatch]:
        return [(names.get(r.sku, r.sku), r.expected_qty, r.counted_qty) for r in rows if r.expected_qty != r.counted_qty]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_service.py -v`
Expected: 19 passed

- [ ] **Step 5: Run the whole suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all passed (60)

- [ ] **Step 6: Commit**

```bash
git add src/stockcount/messages.py src/stockcount/service.py tests/test_service.py
git commit -m "feat: stock counting chat rules and Thai replies"
```

---

### Task 6: LINE webhook app

**Files:**
- Create: `src/stockcount/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `StockService.handle_text / handle_image` (Task 5); `load_config` (Task 1); `SupabaseRepo.from_env()` (Task 8 — imported lazily inside `build_default_app`, so this task's tests do not need it)
- Produces:
  - `LINE_TEXT_LIMIT = 5000`
  - `create_app(service, channel_secret: str, reply: Callable[[str, str], None], fetch_content: Callable[[str], bytes]) -> FastAPI` — `POST /callback`, `GET /health`
  - `build_default_app() -> FastAPI` — production wiring from `.env`; run with `uvicorn stockcount.app:build_default_app --factory`

- [ ] **Step 1: Write the failing test** — `tests/test_app.py`

```python
import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from stockcount.app import LINE_TEXT_LIMIT, create_app

SECRET = "test-secret"


def sign(body: str) -> str:
    return base64.b64encode(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()).decode()


def event(message: dict, source: dict | None = None) -> dict:
    return {
        "type": "message",
        "mode": "active",
        "timestamp": 1727500000000,
        "source": source or {"type": "user", "userId": "U1"},
        "webhookEventId": "01J00000000000000000000000",
        "deliveryContext": {"isRedelivery": False},
        "replyToken": "tok-1",
        "message": message,
    }


TEXT = {"id": "m1", "type": "text", "quoteToken": "q1", "text": "ชั้น A1"}
IMAGE = {"id": "m2", "type": "image", "quoteToken": "q2", "contentProvider": {"type": "line"}}


class StubService:
    def __init__(self, text_reply="ok"):
        self.texts, self.images, self.text_reply = [], [], text_reply

    def handle_text(self, user_id, text):
        self.texts.append((user_id, text))
        return self.text_reply

    def handle_image(self, user_id, content):
        self.images.append((user_id, content))
        return "got image"


def make(service, reply=None):
    replies = []
    app = create_app(
        service,
        SECRET,
        reply or (lambda token, text: replies.append((token, text))),
        lambda message_id: b"bytes-" + message_id.encode(),
    )
    return TestClient(app), replies


def post(client, events):
    body = json.dumps({"destination": "Ubot", "events": events})
    return client.post("/callback", content=body, headers={"X-Line-Signature": sign(body), "Content-Type": "application/json"})


def test_text_is_routed_and_replied():
    svc = StubService()
    client, replies = make(svc)
    assert post(client, [event(TEXT)]).status_code == 200
    assert svc.texts == [("U1", "ชั้น A1")]
    assert replies == [("tok-1", "ok")]


def test_image_content_is_fetched_and_routed():
    svc = StubService()
    client, replies = make(svc)
    post(client, [event(IMAGE)])
    assert svc.images == [("U1", b"bytes-m2")]
    assert replies == [("tok-1", "got image")]


def test_bad_signature_is_rejected():
    client, _ = make(StubService())
    body = json.dumps({"destination": "Ubot", "events": []})
    r = client.post("/callback", content=body, headers={"X-Line-Signature": "wrong", "Content-Type": "application/json"})
    assert r.status_code == 400


def test_verify_request_with_no_events_is_ok():
    client, replies = make(StubService())
    assert post(client, []).status_code == 200
    assert replies == []


def test_group_messages_are_ignored():
    svc = StubService()
    client, replies = make(svc)
    post(client, [event(TEXT, source={"type": "group", "groupId": "G1", "userId": "U1"})])
    assert svc.texts == [] and replies == []


def test_no_reply_when_service_returns_none():
    client, replies = make(StubService(text_reply=None))
    post(client, [event(TEXT)])
    assert replies == []


def test_reply_failure_still_returns_200():
    def broken_reply(token, text):
        raise RuntimeError("Invalid reply token")

    svc = StubService()
    client, _ = make(svc, reply=broken_reply)
    assert post(client, [event(TEXT)]).status_code == 200
    assert svc.texts == [("U1", "ชั้น A1")]


def test_long_reply_is_truncated():
    client, replies = make(StubService(text_reply="ก" * (LINE_TEXT_LIMIT + 50)))
    post(client, [event(TEXT)])
    assert len(replies[0][1]) == LINE_TEXT_LIMIT


def test_health():
    client, _ = make(StubService())
    assert client.get("/health").json() == {"ok": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stockcount.app'`

- [ ] **Step 3: Implement** — `src/stockcount/app.py`

```python
"""FastAPI webhook: verify the LINE signature, route text/image events, reply."""
from __future__ import annotations

import logging
import os
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import ImageMessageContent, MessageEvent, TextMessageContent, UserSource

LINE_TEXT_LIMIT = 5000

log = logging.getLogger(__name__)


def create_app(
    service,
    channel_secret: str,
    reply: Callable[[str, str], None],
    fetch_content: Callable[[str], bytes],
) -> FastAPI:
    parser = WebhookParser(channel_secret)
    app = FastAPI()

    @app.post("/callback")
    async def callback(request: Request):
        body = (await request.body()).decode("utf-8")
        try:
            events = parser.parse(body, request.headers.get("X-Line-Signature", ""))
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="bad signature")

        for event in events:
            # 1:1 chats only; group chats are out of scope for the POC
            if not isinstance(event, MessageEvent) or not isinstance(event.source, UserSource):
                continue
            user_id = event.source.user_id
            if isinstance(event.message, TextMessageContent):
                text = service.handle_text(user_id, event.message.text)
            elif isinstance(event.message, ImageMessageContent):
                text = service.handle_image(user_id, fetch_content(event.message.id))
            else:
                continue
            if text:
                try:
                    reply(event.reply_token, text[:LINE_TEXT_LIMIT])
                except Exception:
                    # counts are already saved; answer 200 so LINE does not keep retrying
                    log.exception("LINE reply failed")
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def build_default_app() -> FastAPI:
    from datetime import datetime, timezone

    from dotenv import load_dotenv
    from linebot.v3.messaging import (
        ApiClient,
        Configuration,
        MessagingApi,
        MessagingApiBlob,
        ReplyMessageRequest,
        TextMessage,
    )

    from .config import load_config
    from .repo import SupabaseRepo
    from .service import StockService

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    api_client = ApiClient(Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]))
    messaging = MessagingApi(api_client)
    blob = MessagingApiBlob(api_client)

    def reply(token: str, text: str) -> None:
        messaging.reply_message(ReplyMessageRequest(reply_token=token, messages=[TextMessage(text=text)]))

    def fetch_content(message_id: str) -> bytes:
        return bytes(blob.get_message_content(message_id))

    service = StockService(
        load_config(os.environ.get("STOCKCOUNT_CONFIG", "config.yaml")),
        SupabaseRepo.from_env(),
        clock=lambda: datetime.now(timezone.utc),
    )
    return create_app(service, os.environ["LINE_CHANNEL_SECRET"], reply, fetch_content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_app.py -v`
Expected: 9 passed. If the v3 parser rejects a sample event, print `parser.parse(...)` error and add the missing field the SDK names to `event()`/`TEXT`/`IMAGE` — do not loosen the signature check.

- [ ] **Step 5: Commit**

```bash
git add src/stockcount/app.py tests/test_app.py
git commit -m "feat: LINE webhook with signature check and safe replies"
```

---

### Task 7: QR labels + helper scripts

**Files:**
- Create: `src/stockcount/qr.py`, `scripts/make_qr.py`, `scripts/import_csv.py`
- Test: `tests/test_qr.py`

**Interfaces:**
- Consumes: `load_config` (Task 1); `load_stock_csv` (Task 2); `build_seed` (Task 2); `parse`, `OpenShelf` (Task 3, test only)
- Produces: `shelf_message(code: str) -> str`, `shelf_url(basic_id: str, code: str) -> str`, `render_label(code: str, url: str, box_size: int = 12) -> PIL.Image.Image`

- [ ] **Step 1: Write the failing test** — `tests/test_qr.py`

```python
from urllib.parse import unquote

from stockcount.parser import OpenShelf, parse
from stockcount.qr import render_label, shelf_message, shelf_url


def test_url_encodes_basic_id_and_prefilled_text():
    url = shelf_url("@abc1234", "A2")
    assert url.startswith("https://line.me/R/oaMessage/%40abc1234/?")
    assert unquote(url.split("?", 1)[1]) == "ชั้น A2"


def test_prefilled_text_parses_as_open_shelf():
    assert parse(shelf_message("B-10")) == OpenShelf("B-10")


def test_label_has_room_for_code_under_qr():
    img = render_label("A2", shelf_url("@abc1234", "A2"))
    width, height = img.size
    assert height > width
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_qr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stockcount.qr'`

- [ ] **Step 3: Implement**

`src/stockcount/qr.py`:
```python
"""LINE deep links and printable QR labels for shelves."""
from __future__ import annotations

from urllib.parse import quote

import qrcode
from PIL import Image, ImageDraw, ImageFont

TEXT_BAND = 130


def shelf_message(code: str) -> str:
    return f"ชั้น {code}"


def shelf_url(basic_id: str, code: str) -> str:
    # oaMessage opens the OA chat with this text pre-filled; staff tap send once
    return f"https://line.me/R/oaMessage/{quote(basic_id, safe='')}/?{quote(shelf_message(code), safe='')}"


def render_label(code: str, url: str, box_size: int = 12) -> Image.Image:
    qr_img = qrcode.make(url, box_size=box_size, border=2).get_image().convert("RGB")
    width, height = qr_img.size
    label = Image.new("RGB", (width, height + TEXT_BAND), "white")
    label.paste(qr_img, (0, 0))
    # shelf codes are A-Z/0-9/-, so Pillow's built-in font is enough (no Thai glyphs needed)
    font = ImageFont.load_default(size=90)
    ImageDraw.Draw(label).text((width // 2, height + TEXT_BAND // 2), code, fill="black", font=font, anchor="mm")
    return label
```

`scripts/make_qr.py`:
```python
"""Write one PNG QR label per shelf into out/qr/.

Usage: .venv/Scripts/python scripts/make_qr.py [config.yaml]
"""
import sys
from pathlib import Path

from stockcount.config import load_config
from stockcount.qr import render_label, shelf_url


def main(argv: list[str]) -> None:
    cfg = load_config(argv[1] if len(argv) > 1 else "config.yaml")
    if "CHANGE-ME" in cfg.line_basic_id:
        sys.exit("Set line_basic_id in config.yaml to the real LINE OA basic ID first.")
    out = Path("out/qr")
    out.mkdir(parents=True, exist_ok=True)
    for code in cfg.shelves:
        path = out / f"shelf-{code}.png"
        render_label(code, shelf_url(cfg.line_basic_id, code)).save(path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv)
```

`scripts/import_csv.py`:
```python
"""Load the stock CSV + config.yaml layout into Supabase.

Usage: .venv/Scripts/python scripts/import_csv.py data/stock_2026-09-28.csv 2026-09-28
"""
import os
import sys
from datetime import date

from dotenv import load_dotenv
from supabase import create_client

from stockcount.config import load_config
from stockcount.seed import build_seed
from stockcount.stock_csv import load_stock_csv


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        sys.exit(__doc__)
    load_dotenv()
    seed = build_seed(load_config("config.yaml"), load_stock_csv(argv[1]), date.fromisoformat(argv[2]))
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    db.table("products").upsert(seed.products, on_conflict="sku").execute()
    db.table("shelves").upsert(seed.shelves, on_conflict="code").execute()
    # the layout in config.yaml is the whole truth: replace, don't merge
    db.table("shelf_products").delete().neq("shelf_code", "").execute()
    db.table("shelf_products").insert(seed.shelf_products).execute()
    db.table("stock_snapshots").upsert(seed.snapshots, on_conflict="sku,as_of").execute()

    print(
        f"products={len(seed.products)} shelves={len(seed.shelves)} "
        f"shelf_products={len(seed.shelf_products)} snapshots={len(seed.snapshots)}"
    )


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_qr.py -v`
Expected: 3 passed

- [ ] **Step 5: Check the label by eye**

Run: `.venv/Scripts/python -c "from stockcount.qr import render_label, shelf_url; render_label('A1', shelf_url('@abc1234','A1')).save('out-test-label.png')"`
Expected: `out-test-label.png` shows a QR with a large `A1` under it. Delete the file afterwards: `rm out-test-label.png`

- [ ] **Step 6: Commit**

```bash
git add src/stockcount/qr.py scripts/make_qr.py scripts/import_csv.py tests/test_qr.py
git commit -m "feat: shelf QR labels and CSV import script"
```

---

### Task 8: Supabase schema, SupabaseRepo, migration Action

**Files:**
- Create: `supabase/migrations/20260928000000_init.sql`, `.github/workflows/db-migrate.yml`, `scripts/smoke_supabase.py`
- Modify: `src/stockcount/repo.py` (append `SupabaseRepo`)
- Generated: `supabase/config.toml` (by `supabase init`)

**Interfaces:**
- Consumes: `Session`, `CountRow`, `UserState`, `Repo` (Task 4)
- Produces: `class SupabaseRepo(client)` implementing every `Repo` method; `SupabaseRepo.from_env() -> SupabaseRepo`; `SupabaseRepo.BUCKET = "shelf-photos"`

No unit test here — `SupabaseRepo` is thin glue over supabase-py and is verified against the real project by `scripts/smoke_supabase.py` (Task 9 runs it once ณัฑฒ์ has created the project).

- [ ] **Step 1: Initialise the Supabase folder**

Run: `npx --yes supabase init`
Expected: creates `supabase/config.toml`. If it asks about VS Code / IntelliJ settings, answer `N`.

- [ ] **Step 2: Write the migration** — `supabase/migrations/20260928000000_init.sql`

```sql
-- Stock count POC (back store, Ladprao branch)

create table products (
  sku      text primary key,
  name     text not null,
  category text not null
);

create table shelves (
  code  text primary key,
  label text not null
);

-- on update cascade: product codes can be corrected later without breaking history
create table shelf_products (
  shelf_code text not null references shelves(code) on update cascade on delete cascade,
  sku        text not null references products(sku) on update cascade,
  position   int  not null,
  primary key (shelf_code, sku)
);

create table stock_snapshots (
  sku      text not null references products(sku) on update cascade,
  back_qty int  not null,
  as_of    date not null,
  primary key (sku, as_of)
);

create table count_sessions (
  id         uuid primary key default gen_random_uuid(),
  count_date date not null unique,
  opened_at  timestamptz not null default now(),
  closed_at  timestamptz
);

create table counts (
  session_id   uuid not null references count_sessions(id) on delete cascade,
  shelf_code   text not null,
  sku          text not null references products(sku) on update cascade,
  expected_qty int  not null,
  counted_qty  int  not null check (counted_qty >= 0),
  line_user_id text not null,
  updated_at   timestamptz not null default now(),
  primary key (session_id, sku)
);

create table user_state (
  line_user_id text primary key,
  shelf_code   text not null,
  opened_at    timestamptz not null
);

create table shelf_photos (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references count_sessions(id) on delete cascade,
  shelf_code   text not null,
  storage_path text not null unique,
  line_user_id text not null,
  created_at   timestamptz not null default now()
);

-- RLS on with no policies: only the service key (server side) can read/write
alter table products        enable row level security;
alter table shelves         enable row level security;
alter table shelf_products  enable row level security;
alter table stock_snapshots enable row level security;
alter table count_sessions  enable row level security;
alter table counts          enable row level security;
alter table user_state      enable row level security;
alter table shelf_photos    enable row level security;

insert into storage.buckets (id, name, public)
values ('shelf-photos', 'shelf-photos', false)
on conflict (id) do nothing;
```

- [ ] **Step 3: Append `SupabaseRepo`** to the end of `src/stockcount/repo.py`, and add `import os` and `import uuid` to the imports at the top of the file

```python
class SupabaseRepo:
    BUCKET = "shelf-photos"

    def __init__(self, client):
        self.db = client

    @classmethod
    def from_env(cls) -> "SupabaseRepo":
        from supabase import create_client

        return cls(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]))

    def get_or_open_session(self, count_date: date, now: datetime) -> Session:
        day = count_date.isoformat()
        self.db.table("count_sessions").upsert(
            {"count_date": day, "opened_at": now.isoformat()}, on_conflict="count_date", ignore_duplicates=True
        ).execute()
        row = self.db.table("count_sessions").select("id,closed_at").eq("count_date", day).single().execute().data
        return Session(id=row["id"], count_date=count_date, closed=row["closed_at"] is not None)

    def close_session(self, session_id: str, now: datetime) -> None:
        self.db.table("count_sessions").update({"closed_at": now.isoformat()}).eq("id", session_id).execute()

    def product_names(self, skus: list[str]) -> dict[str, str]:
        if not skus:
            return {}
        rows = self.db.table("products").select("sku,name").in_("sku", skus).execute().data
        return {r["sku"]: r["name"] for r in rows}

    def expected_back_qty(self, skus: list[str]) -> dict[str, int]:
        if not skus:
            return {}
        rows = (
            self.db.table("stock_snapshots")
            .select("sku,back_qty,as_of")
            .in_("sku", skus)
            .order("as_of", desc=True)
            .execute()
            .data
        )
        latest: dict[str, int] = {}
        for r in rows:
            latest.setdefault(r["sku"], r["back_qty"])
        return latest

    def save_counts(self, session_id: str, rows: list[CountRow], user_id: str, now: datetime) -> None:
        # one upsert statement = the whole shelf or nothing
        payload = [
            {
                "session_id": session_id,
                "shelf_code": r.shelf_code,
                "sku": r.sku,
                "expected_qty": r.expected_qty,
                "counted_qty": r.counted_qty,
                "line_user_id": user_id,
                "updated_at": now.isoformat(),
            }
            for r in rows
        ]
        self.db.table("counts").upsert(payload, on_conflict="session_id,sku").execute()

    def list_counts(self, session_id: str) -> list[CountRow]:
        rows = (
            self.db.table("counts")
            .select("shelf_code,sku,expected_qty,counted_qty")
            .eq("session_id", session_id)
            .execute()
            .data
        )
        return [CountRow(r["shelf_code"], r["sku"], r["expected_qty"], r["counted_qty"]) for r in rows]

    def get_user_state(self, user_id: str) -> UserState | None:
        rows = self.db.table("user_state").select("shelf_code,opened_at").eq("line_user_id", user_id).execute().data
        if not rows:
            return None
        return UserState(shelf_code=rows[0]["shelf_code"], opened_at=datetime.fromisoformat(rows[0]["opened_at"]))

    def set_user_state(self, user_id: str, shelf_code: str, now: datetime) -> None:
        self.db.table("user_state").upsert(
            {"line_user_id": user_id, "shelf_code": shelf_code, "opened_at": now.isoformat()}, on_conflict="line_user_id"
        ).execute()

    def save_photo(self, session_id: str, shelf_code: str, user_id: str, content: bytes, now: datetime) -> str:
        path = f"{session_id}/{shelf_code}/{now:%H%M%S}-{uuid.uuid4().hex[:8]}.jpg"
        self.db.storage.from_(self.BUCKET).upload(path, content, {"content-type": "image/jpeg"})
        self.db.table("shelf_photos").insert(
            {"session_id": session_id, "shelf_code": shelf_code, "storage_path": path, "line_user_id": user_id}
        ).execute()
        return path
```

- [ ] **Step 4: Write the smoke script** — `scripts/smoke_supabase.py`

```python
"""Exercise SupabaseRepo against the real project, then clean up.

Uses the date 2000-01-01 and product SMOKE-1 so real data is never touched.
Usage: .venv/Scripts/python scripts/smoke_supabase.py
"""
from datetime import date, datetime, timezone

from dotenv import load_dotenv

from stockcount.repo import CountRow, SupabaseRepo

DAY = date(2000, 1, 1)


def main() -> None:
    load_dotenv()
    repo = SupabaseRepo.from_env()
    db = repo.db
    now = datetime.now(timezone.utc)
    db.table("products").upsert({"sku": "SMOKE-1", "name": "smoke", "category": "test"}).execute()
    db.table("stock_snapshots").upsert({"sku": "SMOKE-1", "back_qty": 4, "as_of": DAY.isoformat()}).execute()
    try:
        s = repo.get_or_open_session(DAY, now)
        assert repo.get_or_open_session(DAY, now).id == s.id, "second open must reuse the session"
        assert repo.expected_back_qty(["SMOKE-1"]) == {"SMOKE-1": 4}
        repo.save_counts(s.id, [CountRow("Z9", "SMOKE-1", 4, 3)], "U-smoke", now)
        repo.save_counts(s.id, [CountRow("Z9", "SMOKE-1", 4, 4)], "U-smoke", now)
        assert repo.list_counts(s.id) == [CountRow("Z9", "SMOKE-1", 4, 4)], "recount must overwrite"
        repo.set_user_state("U-smoke", "Z9", now)
        assert repo.get_user_state("U-smoke").shelf_code == "Z9"
        path = repo.save_photo(s.id, "Z9", "U-smoke", b"\xff\xd8smoke", now)
        # correcting a sku must cascade into counts
        db.table("products").update({"sku": "SMOKE-2"}).eq("sku", "SMOKE-1").execute()
        assert repo.list_counts(s.id)[0].sku == "SMOKE-2", "on update cascade missing"
        repo.close_session(s.id, now)
        assert repo.get_or_open_session(DAY, now).closed
        db.storage.from_(repo.BUCKET).remove([path])
        print("SMOKE OK")
    finally:
        db.table("count_sessions").delete().eq("count_date", DAY.isoformat()).execute()
        db.table("user_state").delete().eq("line_user_id", "U-smoke").execute()
        db.table("stock_snapshots").delete().in_("sku", ["SMOKE-1", "SMOKE-2"]).execute()
        db.table("products").delete().in_("sku", ["SMOKE-1", "SMOKE-2"]).execute()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Write the migration Action** — `.github/workflows/db-migrate.yml`

```yaml
name: db-migrate
on:
  push:
    branches: [main]
    paths: ["supabase/migrations/**"]
  workflow_dispatch:
jobs:
  migrate:
    runs-on: ubuntu-latest
    env:
      SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
      SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
      SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}
    steps:
      - uses: actions/checkout@v4
      - uses: supabase/setup-cli@v1
        with:
          version: latest
      - run: supabase link --project-ref "$SUPABASE_PROJECT_ID"
      - run: supabase db push
```

- [ ] **Step 6: Make sure nothing else broke**

Run: `.venv/Scripts/python -m pytest -q && .venv/Scripts/python -c "import stockcount.repo as r; print(r.SupabaseRepo.BUCKET)"`
Expected: all passed (72) and `shelf-photos`

- [ ] **Step 7: Commit**

```bash
git add supabase src/stockcount/repo.py scripts/smoke_supabase.py .github/workflows/db-migrate.yml
git commit -m "feat: Supabase schema, SupabaseRepo, smoke script and migration Action"
```

---

### Task 9: Setup guide, to-do, session log (ณัฑฒ์ runs the live steps)

**Files:**
- Create: `C:/Users/User/Documents/CyBrAIn/Guides/guide-setup-stock-count-bot.md`, `C:/Users/User/Documents/CyBrAIn/Avatar project/Code_MD/Code Session 2026-09-28 - Stock Count Phase 1.md`
- Modify: `C:/Users/User/Documents/CyBrAIn/To-do List.md`, `Code_MD/Code Hub - Avatar.md`, `Code_MD/Project - Stock Count.md`

**Interfaces:**
- Consumes: everything above (commands, file names, env var names)
- Produces: the guide ณัฑฒ์ follows to make the bot live

- [ ] **Step 1: Write the guide** — `Guides/guide-setup-stock-count-bot.md`, in Thai, same shape as `Guides/guide-install-checkin-system.md` (read it first): properties (`tags`, `aliases`, `created: 2026-09-28`, `status: active`), ⏱️ ~90 นาที (แบ่งทำได้ 4 ช่วง), 🎯 done-when = "สแกน QR ชั้น A1 ด้วยมือถือ → bot ตอบรายการ → พิมพ์ยอด → เห็นแถวใน Supabase ตาราง `counts`", 🧰 needs (บัญชี GitHub, Supabase, LINE, ngrok, มือถือที่มี LINE), "▶️ เริ่มตรงนี้" = เปิด https://github.com/new แล้วตั้งชื่อ repo `stock-count` (private), one action per checkbox, light self-referential humour, 🆘 troubleshooting. Sections and their checkboxes:
  1. **GitHub** — create private repo `stock-count`; in `Avatar project/stock-count/` run `git remote add origin <url>` then `git push -u origin main`; open the Actions tab and see `tests` go green.
  2. **Supabase** — create project (free, region Singapore); copy Project ID (Settings → General), Project URL + `service_role` key (Settings → API), DB password (the one set at creation); create an access token at Account → Access Tokens; add GitHub repo secrets `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, `SUPABASE_PROJECT_ID`; Actions → `db-migrate` → Run workflow → green; Table Editor shows 8 tables.
  3. **LINE** — create LINE Official Account (LINE Official Account Manager); Settings → Messaging API → Enable; note Basic ID (`@…`); in LINE Developers console copy Channel secret (Basic settings) and issue a long-lived Channel access token (Messaging API tab); in OA Manager turn **off** auto-reply and greeting messages (else the bot's replies get doubled).
  4. **Run locally** — `cp .env.example .env` and fill the 4 values (never commit `.env`); put the Basic ID into `config.yaml` → `line_basic_id`; `.venv/Scripts/python scripts/smoke_supabase.py` → `SMOKE OK`; `.venv/Scripts/python scripts/import_csv.py data/stock_2026-09-28.csv 2026-09-28`; `.venv/Scripts/uvicorn stockcount.app:build_default_app --factory --port 8000`; in a 2nd terminal `ngrok http 8000`; paste `https://<ngrok>/callback` as Webhook URL, turn on "Use webhook", press Verify → Success.
  5. **Try it** — add the OA as friend from the phone; `.venv/Scripts/python scripts/make_qr.py`; open `out/qr/shelf-A1.png` on the computer screen, scan it with the phone's LINE camera, tap send; type the numbers; send a photo; type `สรุป`.
  - 🆘 rows: Verify fails → server/ngrok not running or URL missing `/callback`; bot replies twice → auto-reply still on; bot silent → `LINE_CHANNEL_SECRET` wrong (server log shows 400) or user not in `allowed_line_user_ids`; `SeedError` → a SKU in `config.yaml` is not in the CSV; ngrok URL changes each restart → re-paste the webhook URL; `db-migrate` red → one of the 3 secrets missing/typo.

- [ ] **Step 2: Add to-dos** — in `To-do List.md` under `## 💻 ใช้คอม` → `### 🟡 สัปดาห์นี้`, matching existing line style, bump `updated:` to 2026-09-28:
  - `ตั้งค่า bot นับสต็อกให้ใช้ได้จริง (GitHub + Supabase + LINE + ngrok) 📘 [[guide-setup-stock-count-bot]] 🗓️ 2026-09-28 ⏱️ 90 นาที`
  - `เดินจดผังชั้นหลังร้าน (ชั้นไหนมีสินค้าอะไร เรียงยังไง) แล้วแก้ config.yaml 🗓️ 2026-09-28 ⏱️ 30 นาที`
  - `ตรวจชื่อสินค้า 2 ตัวใน data/stock_2026-09-28.csv ที่ needs_review=true (HB0083, NA0031) 🗓️ 2026-09-29 ⏱️ 5 นาที`
  - `จับเวลานับสต็อกหลังร้านแบบกระดาษ 1 รอบ (baseline เทียบกับ 15 นาที) 🗓️ 2026-09-28 ⏱️ 15 นาที`
  - and under `### 🤔 ตัดสินใจเอง`: `ถามหัวหน้าก่อนแปะ QR ที่ชั้น + ใช้ LINE OA ของใคร (ส่วนตัว/บริษัท) 🗓️ 2026-09-28 ⏱️ 10 นาที`

- [ ] **Step 3: Write the session log** — `Code_MD/Code Session 2026-09-28 - Stock Count Phase 1.md` using the template at the bottom of `Code Hub - Avatar.md` (TL;DR · what/which files · decisions + why · ❓ open questions). Decisions to record: LINE chat not LIFF (Python only), QR per shelf, YAML config, show system qty (no blind count), 28/9 sheet with real codes replaced the TEMP codes, Action instead of built-in integration (free plan), on-update-cascade, OCR dropped. Open questions: deploy target, LINE OA owner, permission to put up QR, real shelf layout.

- [ ] **Step 4: Update hubs** — top of "บันทึกแต่ละรอบ" in `Code Hub - Avatar.md` gets the session link; the Stock Count row status becomes `🟡 โค้ดเสร็จ · รอติดตั้ง`; in `Project - Stock Count.md` set `status: waiting`, `status_note: "โค้ดเสร็จ · รอติดตั้ง"`, add the guide + plan links to "อยู่ไหน", replace the log line with the session link.

- [ ] **Step 5: Final check and commit (repo only — vault notes are outside the repo)**

Run: `.venv/Scripts/python -m pytest -q && git status --short`
Expected: all passed (72) and `git status --short` prints nothing (the vault notes from Steps 1–4 live outside `stock-count/`, so they don't show up here).
```bash
git log --oneline | head -12
```
Expected: the 8 feature commits from Tasks 1–8 on top of the spec commits.
