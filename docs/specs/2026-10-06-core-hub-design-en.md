---
tags: [spec, code, avatar-clinic, hub, english]
aliases: [Core hub spec (EN)]
status: draft
status_note: "English companion of the 6/10 Thai spec — the Thai file is the source of truth if they ever differ"
created: 2026-10-06
---
# 🏛️ Spec — the core hub of the `Avatar_clinic` company repo

← [[Project - Avatar Clinic Hub]] · [[Code Hub - Avatar]] · 🇹🇭 ภาษาไทย: [[2026-10-06-core-hub-design]]

## TL;DR
`main` is the company hub: guidelines every system shares, internal tools (the part-time check-in) and analytics code (the Gen Z capstone). Deployable services with their own life cycle (stock count) keep their own branch and are listed in the "Services" table of the front README.

## What ณัฑฒ์ said vs what Claude decided
| ณัฑฒ์ said (6/10) | Claude decided (ณัฑฒ์ asked for freestyle) · why |
|---|---|
| main = the central hub, "the core" | Folders `tools/`, `analytics/`, `docs/`, `.github/` — grouped by kind of work, easy to find |
| Put the check-in tool there | **Moved**, not copied → `tools/checkin/` — one home, nothing to edit twice |
| Core = shared docs + the capstone code | Copied only committed capstone code (commit `dd88055`) → `analytics/genz-capstone/` · **the capstone repo is untouched** (it holds uncommitted work by ณัฑฒ์) |
| Licence "company-only, no outside use" (given for stock count) | Applied to main too, replacing Apache-2.0 — the whole repo belongs to the company |
| — | Work on branch `core-hub` → ณัฑฒ์ pushes and opens a PR into main, so the diff is reviewed on GitHub before merging |
| — | No shared code library yet — ณัฑฒ์ did not pick it, and only one system would use it |

## Layout
```
Avatar_clinic (main)
├── README.md                     map of every system · how to start
├── LICENSE                       company-only
├── .github/
│   ├── CONTRIBUTING.md           how we work (branches · commits · PRs · tests · docs)
│   ├── SECURITY.md               secrets · personal data (PDPA) · ≤ 5 countries · reporting
│   ├── CODEOWNERS · pull_request_template.md
│   └── workflows/ci.yml          check-in tests (Node) + analytics tests (Python)
├── tools/checkin/                part-time check-in → Google Sheet + Slack
├── analytics/genz-capstone/      survey · CVA · baseline (Python)
└── docs/specs/                   hub specs (this file)

service branches: Stock-count-fork  ← stock count (forked from main · deployed on Railway)
```
- `CONTRIBUTING.md` / `SECURITY.md` live in `.github/`: GitHub still finds them, and Obsidian does not add them as notes to the vault (note names must stay unique)

## Why this shape (options considered)
| Option | Pros | Cons | Result |
|---|---|---|---|
| **A. main = hub + tools + analytics · deployable services on branches** | Matches ณัฑฒ์'s description · main stays easy to read · services deploy independently | Both sides own the root files (README, CI) → service branches **do not merge main**; a shared change is copied in through a small PR | ✅ chosen |
| B. Everything in main (`services/stock-count/`) | One place · one PR shows everything | Moves stock count's CI / Railway / Supabase paths in the middle of the pilot | Reconsider after the pilot |
| C. A + a shared core library | Reuse | Only one consumer (YAGNI) · not picked by ณัฑฒ์ | ❌ for now |

## Shared rules (full text in `.github/CONTRIBUTING.md` and `.github/SECURITY.md`)
- **Branches:** `main` = hub · a service = its own branch forked from main (e.g. `Stock-count-fork`) · small work on `feat/…` `fix/…` `docs/…` → PR
- **Commits:** Conventional Commits (`feat:` `fix:` `docs:` `test:` `chore:` `ci:`) · every PR passes CI · new behaviour arrives with a test written first
- **Data:** may pass through ≤ 5 countries (today Thailand · Japan · Singapore · United States) · personal data (PDPA: photos of people, audio, consent forms, raw answers) is never committed · secrets live only in env vars / Script Properties / Railway variables · the repo is private
- **Docs:** dated specs and plans · Thai is the source, with an English companion · READMEs in English

## CI (`.github/workflows/ci.yml`)
- Runs when `tools/`, `analytics/` or the workflow itself changes (path filters — pushes to other services skip it)
- **checkin:** Node 22 → `node --test "tools/checkin/tests/*.test.js"` (9 tests)
- **analytics:** Python 3.12 → `pip install -r requirements.txt` → `pytest -q` (37 tests · synthetic data, since real data never enters git)

## Risks / not verified ⚠️
- The capstone code temporarily lives in two places (the old capstone repo + main) → ณัฑฒ์ decides whether to delete `code/` in the capstone repo or keep it read-only
- CI has not run on GitHub yet · `opencv-python` is not imported during the tests (the import sits inside a function), so no system graphics libraries are needed
- The deployed check-in tool lives in Google Apps Script, not git — after changing the code here it has to be pasted into Apps Script again

## ❓ For ณัฑฒ์ to decide on return
1. **Merge PR `core-hub` into main?** (review the diff on GitHub first)
2. **Capstone code:** delete `code/` in the old capstone repo (main becomes the only home) or keep it
3. **Service branch names:** keep `<Service>-fork`, or switch to `service/<name>`
