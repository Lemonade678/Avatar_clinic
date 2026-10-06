# Contributing

How we work in the Avatar Clinic repository. Short on purpose: if a rule is missing, follow the spirit of the ones here and add it in the same pull request.

## Branches
| Branch | Holds | Merges into |
|---|---|---|
| `main` | The hub: guidelines, internal tools (`tools/`), analytics (`analytics/`), docs | — (protected by review) |
| `<Service>-fork` (e.g. `Stock-count-fork`) | One deployable service with its own CI and deploy target, forked from `main` | its own deploy; `main` only through a reviewed PR |
| `feat/…` `fix/…` `docs/…` `chore/…` | One focused change | the branch it started from |

- A new service gets its own branch forked from `main`, plus one row in the **Services** table of the front README.
- Service branches merge `main` now and then to pick up shared changes (`git merge origin/main`).
- Never force-push a shared branch. If a push is rejected, fetch and integrate first.

## Commits
[Conventional Commits](https://www.conventionalcommits.org): `feat:` `fix:` `docs:` `test:` `refactor:` `perf:` `ci:` `chore:`, imperative mood, the *why* in the body when it is not obvious. One logical change per commit.

## Pull requests
- Fill in the template: what changes, why, how it was tested.
- CI must be green. New behaviour arrives with a test that failed before the change.
- Database changes ship as a **new** migration; applied migrations are never edited.
- Keep secrets, personal data and real photos out of the diff (see [SECURITY.md](SECURITY.md)).

## Tests
| Area | Command |
|---|---|
| `tools/checkin` | `node --test "tools/checkin/tests/*.test.js"` |
| `analytics/genz-capstone` | `cd analytics/genz-capstone && python -m pytest -q` |
| a service branch | see that branch's README |

## Code style
- UTF-8 everywhere, LF line endings for code (`.gitattributes`, `.editorconfig`).
- Python 3.12; JavaScript runs in Google Apps Script (V8) and Node 22 for tests.
- Identifiers and code comments in English; user-facing text in Thai.

## Documents
- Design changes are written as a dated spec (`docs/specs/YYYY-MM-DD-<topic>-design.md`): Thai is the source of truth, with an English companion (`…-en.md`).
- A spec records what was asked, what was decided and why, and the open questions.
- READMEs are in English and describe how to run and change the code.
