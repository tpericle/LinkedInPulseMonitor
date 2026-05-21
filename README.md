# LinkedIn Pulse Monitor

A local-first prototype for monitoring a small curated set of important LinkedIn people, finding their new posts, and helping Tony engage quickly without relying on the LinkedIn feed.

## v0 Goal

- Track a curated list of important LinkedIn profile URLs.
- Fetch only new/recent posts from those individuals, starting with manual guarded Apify runs.
- Store minimal operational state: tracked people, seen post IDs, and a short recent cache.
- Summarize each new post and include a direct LinkedIn link.
- Provide a lightweight dashboard/feed so Tony can review and engage quickly.

This repo is built in small, teachable increments using agent-assisted software development.

## Current status

Phase 0/1 foundation is underway:

- FastAPI app shell
- `/health` endpoint
- `/dashboard` page using Jinja2 + Tailwind CDN
- SQLAlchemy database setup
- Initial provider-neutral tables
- pytest foundation tests
- Apify spike helper and sample fixture
- Apify parser that normalizes recent actor items into provider-neutral post inputs
- Pipeline that connects raw Apify items to SQLite ingestion
- Ingestion layer that stores parsed posts in SQLite and skips duplicates
- Tracked profile service plus profile creation API
- Mock daily report generator plus report generation API
- Dashboard sections for tracked profiles, recent posts, and latest report
- Dashboard admin form for adding validated LinkedIn profiles
- Dashboard action for generating today’s mock report

## Local setup

This project requires Python 3.12 or newer.

On this Mac, use the Homebrew Python already installed:

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

## Run the app

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

## Run tests

```bash
source .venv/bin/activate
pytest -q
```

## Run lint

```bash
source .venv/bin/activate
ruff check .
```

## First Apify spike profiles

We will use these profiles for the initial data spike:

- https://www.linkedin.com/in/arthur-c-brooks/
- https://www.linkedin.com/in/danielpink/
- https://www.linkedin.com/in/dharmesh/

## Development approach

- Use feature branches.
- Prefer small commits.
- Write tests before implementation when adding behavior.
- Keep Apify-specific logic isolated under `app/sources/`.
- Use manual guarded real-data runs before scheduling Apify checks.
- Prefer reliable/flexible LinkedIn data sources even if they cost more; validate with measured runs before committing.
- Notify only when new posts are found; avoid no-post notifications except during testing.
- Keep AI/report generation mock-only until real provider keys are intentionally added.

## Plan

See `docs/plans/2026-05-21-engagement-feed-plan.md` for the current product plan and next phases.
