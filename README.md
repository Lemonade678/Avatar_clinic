# Avatar Clinic — Engineering

[![ci](https://github.com/Lemonade678/Avatar_clinic/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Lemonade678/Avatar_clinic/actions/workflows/ci.yml)

The central repository for Avatar Clinic's internal software: shared engineering guidelines, internal tools and analytics code. Deployable services live on their own branches and are listed under [Services](#services).

| | |
|---|---|
| **Visibility** | Private · internal use only |
| **Default branch** | `main` (this hub) |
| **Owner** | Avatar Clinic tech team · maintainer [@Lemonade678](https://github.com/Lemonade678) |

## What lives in `main`
| Path | What it does | Stack | Status |
|---|---|---|---|
| [`tools/checkin/`](tools/checkin/) | Part-time check-in: a private web page logs each work session to a Google Sheet and posts the daily scrum to Slack `#avatar-scrum-daily` | Google Apps Script | In use |
| [`analytics/genz-capstone/`](analytics/genz-capstone/) | Gen Z neck-health capstone: survey pipeline, craniovertebral-angle (CVA) prototype, Facebook Insights baseline | Python 3.12 · pandas · SciPy | Research · runs on synthetic data |
| [`docs/specs/`](docs/specs/) | Design specs for this hub (Thai, with English companions) | Markdown | — |
| [`.github/`](.github/) | How we work, security and data policy, PR template, CI | — | — |

## Services
Each deployable service has its own branch, CI and deploy target. Switch to the branch to see its README.

| Service | Branch | What it does | Stack | Status |
|---|---|---|---|---|
| Stock Count | [`Stock-count-fork`](https://github.com/Lemonade678/Avatar_clinic/tree/Stock-count-fork) | Back-store stock counting inside LINE with a computer-vision cross-check and two-year shelf-life tracking | Python 3.12 · FastAPI · Supabase · Roboflow · Railway | Pilot · MBK branch |

## Getting started
```bash
git clone https://github.com/Lemonade678/Avatar_clinic.git
cd Avatar_clinic
node --test "tools/checkin/tests/*.test.js"
```
```bash
cd analytics/genz-capstone
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q
```
On macOS/Linux use `.venv/bin/python`. For a service: `git switch Stock-count-fork` and follow its README.

## How we work
Branches, commits, pull requests, tests and documents: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security and data
Secrets, personal data (PDPA), the five-country rule and how to report a problem: [.github/SECURITY.md](.github/SECURITY.md).

## License
Proprietary. © 2026 Avatar Clinic. All rights reserved; internal use only. See [LICENSE](LICENSE).
