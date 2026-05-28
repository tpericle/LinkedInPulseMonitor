# LinkedIn Pulse Monitor

A local-first prototype for monitoring a small curated set of important LinkedIn people, finding their new posts, and helping Tony engage quickly without relying on the LinkedIn feed.

This repo is also a learning project: it is built in small, teachable increments using agent-assisted software development.

## What this app is for

LinkedIn Pulse Monitor should help Tony answer:

- Who important posted recently?
- What did they say?
- Which posts are worth opening directly on LinkedIn?
- What themes are emerging across the people Tony follows?
- What should Tony pay attention to or engage with soon?

The current v0 is intentionally simple. It is not a broad analytics platform, CRM, or production SaaS.

## v0 goal

- Track a curated list of important LinkedIn profile URLs.
- Fetch only new/recent posts from those individuals, starting with manual guarded Apify runs.
- Store minimal operational state: tracked people, seen post IDs, scrape runs, reports, and recent posts.
- Summarize useful activity from the last 24 hours.
- Provide a lightweight dashboard/feed so Tony can review and engage quickly.

## Current status

The prototype currently includes:

- FastAPI app shell.
- `/health` endpoint.
- `/dashboard` page using Jinja2 + Tailwind CDN.
- SQLAlchemy database setup.
- Initial provider-neutral tables.
- pytest foundation tests.
- Apify spike helper and sample fixture.
- Apify parser that normalizes recent actor items into provider-neutral post inputs.
- Pipeline that connects raw Apify items to SQLite ingestion.
- Ingestion layer that stores parsed posts in SQLite and skips duplicates.
- Tracked profile service plus profile creation API.
- Mock daily report generator plus report generation API.
- Dashboard sections for tracked profiles, recent posts, and latest report.
- Dashboard admin form for adding validated LinkedIn profiles.
- Guarded manual Apify fetch service and CLI.
- Dashboard action for fetching latest posts now with cost/count confirmation.
- Dashboard action for generating today’s mock report.
- Seed script for the three starter profiles.
- Real Apify fetch path validated.
- Dashboard reorganized around the priority feed and tracked people.
- Dashboard profile administration for adding, editing display names/URLs, pausing/reactivating, and deleting paused profiles.
- Active profile safety limit of 10, with clear warnings when adding/reactivating would exceed the limit.
- Admin add/edit/pause/reactivate/delete actions use encoded post/redirect/get confirmations, return to the administration section, and require browser confirmation for pause/reactivate/delete where appropriate.
- Manual dashboard fetch now uses a confirmation step before execution, lists active profiles, explains normal 24-hour fetches, and gives newly added profiles a one-time 7-day initial lookback.
- One-command daily cycle service and script for guarded fetch + mock report generation.
- Commentary profile reader for `docs/profile/tony-commentary-style.md`.
- Mock comment starter prompts on priority-feed cards, explicitly framed as thinking prompts rather than copy-paste comments.

## Current dashboard flow

The dashboard is organized as:

1. **Priority feed**
   - Recent saved posts from the last 7 days.
   - Manual fetch button.
   - Post cards with author, date, review/age badges, preview/hook, direct LinkedIn link, and mock comment starter ideas.

2. **People we follow**
   - Active tracked profiles.
   - Currently seeded starter profiles: Arthur Brooks, Daniel Pink, Dharmesh Shah.

3. **Profile administration**
   - Add a new tracked LinkedIn profile.
   - Edit display names and LinkedIn URLs.
   - Pause profiles you no longer want to monitor.
   - Reactivate paused profiles later.
   - Delete profiles only after they are paused.
   - Paused profiles stay in the local database but are excluded from fetches.

4. **Daily report**
   - Mock/no-op by default until a real AI provider is intentionally configured.

## Product conventions

- Daily scrape/report logic defaults to the **last 24 hours**.
- Dashboard recent-post review can show a **7-day window** so there is something useful to inspect.
- Apify may return older posts; the app should filter older posts out by default for normal daily use.
- Manual guarded Apify runs come before scheduling.
- Notify only when new posts are found once notifications are added.
- Use mock report generation until real AI keys are intentionally added.
- Keep the app local-first and easy to understand.

## Local setup

This project requires Python 3.12 or newer.

On this Mac, the Homebrew Python path has been used successfully:

```bash
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create your local environment file:

```bash
cp .env.example .env
```

Then fill in local-only secrets such as `APIFY_TOKEN`. Do not commit `.env`.

If `uv` is available and the environment is already configured, the project can also be run with `uv run` commands.

## Run the app

With an activated venv:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/dashboard
```

Health check:

```text
http://localhost:8000/health
```

## Seed starter profiles

The current starter profiles are:

- Arthur Brooks — `https://www.linkedin.com/in/arthur-c-brooks/`
- Daniel Pink — `https://www.linkedin.com/in/danielpink/`
- Dharmesh Shah — `https://www.linkedin.com/in/dharmesh/`

Seed them with:

```bash
uv run python scripts/seed_sample_profiles.py
```

or, if using an activated venv without `uv`:

```bash
python scripts/seed_sample_profiles.py
```

## Run a guarded manual Apify fetch

From the CLI:

```bash
source .venv/bin/activate
python scripts/manual_apify_fetch.py --limit-per-source 3 --max-total-charge-usd 1.00
```

A prior review run used a wider explicit lookback to populate dashboard data:

```bash
uv run python scripts/manual_apify_fetch.py --lookback-hours 72 --limit-per-source 10 --max-total-charge-usd 1.00
```

## Run a daily fetch + report cycle

Use this after the active profile list and Apify guardrails feel right. It runs the guarded Apify fetch and then generates the mock daily report:

```bash
uv run python scripts/daily_cycle.py
```

The recap is intentionally reviewable before scheduling. Check:

- how many active profiles were checked
- how many Apify items came back
- how many posts parsed, inserted, or skipped
- provider status
- estimated Apify cost
- generated report id
- whether the future notification behavior should notify Tony or stay quiet

Normal daily behavior should remain last-24-hours unless an explicit backfill/review run is requested.

## Run tests

With an activated venv:

```bash
pytest -q
```

With `uv`:

```bash
uv run pytest -q
```

## Run lint

With an activated venv:

```bash
ruff check .
```

With `uv`:

```bash
uv run ruff check .
```

Latest known verification from this session:

```text
uv run pytest -q      -> 62 passed
uv run ruff check .   -> All checks passed
```

## Development approach

- Use feature branches.
- Prefer small commits.
- Write tests before implementation when adding behavior.
- Keep Apify-specific logic isolated under `app/sources/`.
- Use manual guarded real-data runs before scheduling Apify checks.
- Prefer reliable/flexible LinkedIn data sources even if they cost more; validate with measured runs before committing.
- Keep AI/report generation mock-only until real provider keys are intentionally added.
- Keep the codebase teachable.

## Documentation map

- `README.md` — human-facing setup, usage, status, and review instructions.
- `AGENTS.md` — agent-facing project context, conventions, architecture notes, and progress log.
- `docs/plans/` — implementation/product plans.
- `docs/profile/tony-commentary-style.md` — editable markdown source for Tony's profile, point of view, and future comment starter guidance.
- `spikes/` — exploratory integration notes.
- `tests/fixtures/` — sample Apify/mock data and fixture notes.

## Plan

See:

- `docs/plans/2026-05-21-engagement-feed-plan.md` for the original engagement feed plan.
- `docs/plans/2026-05-23-regular-runs-admin-commentary.md` for the next plan covering regular runs, administration/archive, and markdown-based commentary guidance.

## Current review focus

Refresh the dashboard:

```text
http://127.0.0.1:8000/dashboard
```

Use hard refresh if needed:

```text
Cmd + Shift + R
```

Review:

1. Add or edit a profile and confirm the interface clearly shows that it will be included in the next fetch.
2. Use **Review fetch details** and confirm the fetch confirmation explains active profiles, 24-hour normal lookback, 7-day initial lookback for new profiles, limits, and skip behavior.
3. Execute the fetch and confirm the recap makes saved/skipped/no-new-post outcomes understandable.
4. Pause a test profile and confirm delete is available only after it is paused.

Recommended next development focus:

- Have Tony test whether the new fetch confirmation/result recap removes the “nothing happened” feeling after adding a new profile.
- Consider simple event/live-presentation detection callouts before adding email or calendar automation.
- Start replacing mock comment starters with more personalized guidance as Tony provides fuller Markdown profile/voice files.

## Progress log

### 2026-05-27 — Profile management and fetch confirmation UX

- Added a two-step dashboard fetch flow: **Review fetch details** then **Execute fetch**.
- Fetch confirmation now lists active profiles, explains the normal 24-hour lookback, gives newly added profiles a one-time 7-day lookback, and states Apify/active-profile guardrails.
- Raised the active-profile safety limit to 10 and added clear handling when adding/reactivating would exceed the limit.
- Simplified profile UI by hiding company/tags, adding edit display-name/URL controls, renaming archive to pause tracking, and allowing delete only after pause while keeping historical posts.
- Added `docs/plans/2026-05-27-profile-fetch-ux.md`.
- Verified with `uv run pytest -q` (62 passed) and `uv run ruff check .`.

### 2026-05-24 — Comment starters and reviewable daily cycle recap

- Added mock comment starter ideas to priority-feed cards, using the markdown commentary profile reader and clearly labeling them as thinking prompts rather than copy-paste comments.
- Made the daily-cycle recap more reviewable before scheduling by listing what ran, estimated Apify cost, report id, and whether future notification behavior should notify Tony or stay quiet.

### 2026-05-24 — Admin confirmations, daily cycle, and commentary reader

- Improved profile administration with browser confirmations for archive/reactivate, encoded PRG redirects back to the administration section, and clearer action confirmation text.
- Added `scripts/daily_cycle.py` and `app/daily_cycle.py` for a one-command guarded fetch + mock report cycle.
- Added `app/commentary_profile.py` so code can read and sectionize Tony's markdown commentary profile.
- Latest verification: `.venv/bin/pytest -q` -> 53 passed; `.venv/bin/ruff check .` -> All checks passed.

### 2026-05-23 — Administration slice and next-step plan added

- Added dashboard administration for profile add/archive/reactivate.
- Added `docs/profile/tony-commentary-style.md` as the editable markdown starting point for Tony's future comment guidance.
- Added `docs/plans/2026-05-23-regular-runs-admin-commentary.md` covering regular runs, administration, and commentary suggestions.

### 2026-05-23 — Priority-feed review badges added

- Added `Review today` / `Review window` badges and relative age labels to priority-feed post cards.
- Verified the dashboard remains easy to scan in the browser.

### 2026-05-22 — Project context documentation added

- Added `AGENTS.md` as the durable project context and agent handoff document.
- Updated `README.md` to be the human-facing setup, usage, status, and review document.
- Going forward, meaningful project progress should be appended to `AGENTS.md` and summarized here when it affects setup, usage, status, or review instructions.
