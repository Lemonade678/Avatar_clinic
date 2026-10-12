# Part-time check-in

A private web page for part-time work sessions. Check in with today's plan, check out with what got done; every session becomes one row in a Google Sheet and two messages in Slack `#avatar-scrum-daily` (the daily scrum: yesterday · today · blockers).

## How it works
```
[web page, Apps Script] ──▶ Code.gs ──▶ Google Sheet, tab "Log" (one row = one work session)
                                    └──▶ Slack incoming webhook → #avatar-scrum-daily
```
- **One row per session**, so a day with several sessions works.
- **Forgot to check out?** Enter the time by hand; the row is flagged `edited` and Slack says so.
- **Slack down?** The Sheet is written first; the Slack result is stored in `slack_in` / `slack_out`, so no session is lost.
- Week starts on Monday · Bangkok time · text is capped at 2,000 characters and cells that start with `= + - @` are escaped so the Sheet never runs them as formulas.

## Files
| File | Purpose |
|---|---|
| `Code.gs` | Server side: sheet I/O, Slack posts, pure helpers (tested) |
| `Index.html` | The web page (today · history with weekly/monthly hours, chart, CSV) |
| `appsscript.json` | Manifest: Bangkok time zone, minimal OAuth scopes, web app runs as the deployer and only for them |
| `tests/logic.test.js` | Node tests for the pure helpers |

## Set up
1. Create a Slack app with an incoming webhook to `#avatar-scrum-daily`.
2. Create a Google Sheet → **Extensions → Apps Script** → paste `Code.gs`, `Index.html`, `appsscript.json`.
3. **Project settings → Script properties:** `SLACK_WEBHOOK_URL` = the webhook. The webhook is a secret: never put it in the code.
4. Run `setup`, then `testSlack` → a test message appears in Slack.
5. **Deploy → New deployment → Web app** (execute as: me · access: only myself) → bookmark it on the phone.

The deployed copy lives in Apps Script, not git: after changing the code here, paste it into Apps Script and create a new deployment version.

## Test
```bash
node --test "tools/checkin/tests/*.test.js"
```
