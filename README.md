# LinkedIn Pulse Monitor

A local-first prototype for tracking LinkedIn profiles, ingesting recent posts through Apify, and generating daily AI summaries and themes.

## v0 Goal

- Track a list of LinkedIn profile URLs.
- Scrape recent posts through Apify.
- Store new posts in SQLite.
- Generate daily AI summaries from the last 24 hours.
- View posts and reports in a lightweight FastAPI dashboard.

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
- Keep AI report generation mock-only until real provider keys are intentionally added.
