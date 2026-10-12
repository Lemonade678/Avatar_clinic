# Security and data policy

## Reporting a problem
Report security problems or data leaks **privately** to the maintainer ([@Lemonade678](https://github.com/Lemonade678)), never in an issue or a pull request. Include what you found, where, and since when. If a secret was exposed, rotate it first and report second.

## Secrets
- Secrets live only in environment variables (`.env` locally, Railway variables), GitHub Actions secrets, or Google Apps Script *Script Properties* — never in code, config files, notes, chat or AI prompts.
- `.env` is git-ignored; commit an `.env.example` with names only.
- A secret that appeared anywhere it should not (a commit, a screenshot, a chat) is treated as leaked and rotated, even if the commit is deleted.
- Logs must not print secrets (for example, an HTTP client logging request URLs that carry an API key).

## Personal data (PDPA)
- Photos of people, audio recordings, consent forms, interview lists and raw survey answers never enter git. Keep them in `private/` folders or outside the repo; both are git-ignored.
- Analytics code runs on synthetic data in tests; anything synthetic is labelled **SYNTHETIC** or **SIMULATION**.
- Collect consent before photographing anyone; keep the minimum needed and delete it when the study ends.

## Where data may go
Data may pass through **at most five countries**. Today that is four:

| Country | Services |
|---|---|
| Thailand | branches, staff phones and computers |
| Japan | LINE (LIFF, Messaging API) |
| Singapore | Supabase, Railway |
| United States | GitHub, Roboflow, Google (Apps Script, Sheets)¹, Slack¹, Anthropic |

¹ Google and Slack may also keep data in other regions; not yet verified for our accounts.

A new vendor must fit within these countries or keep the total at five or fewer, and is added to this table in the same pull request.

## Access
- The repository is **private**: it holds real business data. Check visibility before pushing anything that contains data.
- Production apps restrict who can sign in (for example, an allow-list of LINE user IDs).
- Database tables keep row-level security on; only server-side code holds service keys.
