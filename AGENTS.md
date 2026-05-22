# AGENTS.md — LinkedIn Pulse Monitor Project Context

This file is the working context document for AI agents contributing to LinkedIn Pulse Monitor. Read it before planning or changing code in this repository.

## Project identity

- **Project:** LinkedIn Pulse Monitor
- **Repo:** `/Users/anthonypericle/workspace/LinkedInPulseMonitor`
- **GitHub:** `tpericle/LinkedInPulseMonitor`
- **Owner / learner:** Tony Pericle
- **Primary goal:** Build a working local-first prototype while teaching Tony how agent-assisted software development works.

This is both a product prototype and a learning project. Make small, reviewable changes; explain the reasoning; keep code easy to inspect.

## North Star

LinkedIn Pulse Monitor helps Tony follow a small curated set of important LinkedIn people without relying on the LinkedIn feed.

The product should:

1. Track selected LinkedIn profile URLs.
2. Fetch recent posts through Apify.
3. Store new posts locally.
4. Summarize useful activity from the last 24 hours.
5. Present a lightweight dashboard/feed with direct links so Tony can review and engage quickly.

The product direction is not broad analytics. It is a practical near-real-time engagement helper for a curated set of important people.

## Teaching goals

Every development session should reinforce the process:

- Clarify requirements before building.
- Scope the next small increment.
- Use feature branches and small commits.
- Inspect generated code instead of blindly trusting it.
- Run tests and lint.
- Use fixtures and raw JSON to debug integrations.
- Keep external-service risk isolated behind adapters.
- Avoid overbuilding v0.

When presenting results to Tony, include:

- What changed.
- How it was tested.
- What commit/branch changed, if relevant.
- What Tony should review next.
- Recommended next step, limited to the next one to three increments.

## Current stable requirements

### In scope for v0

- Local-first Python web app.
- FastAPI backend.
- SQLite database via SQLAlchemy.
- Jinja2 templates and Tailwind CDN.
- Apify-backed LinkedIn scraping, isolated behind source adapters.
- Mock data/reporting path when external API keys are missing.
- Tracked profiles.
- Recent post ingestion with duplicate skipping.
- Raw Apify JSON stored for inspection and parser fixes.
- Dashboard with recent posts, tracked people, scrape/fetch status, and daily report.
- Daily report generation from posts in the last 24 hours.

### Out of scope for v0

- Email delivery.
- Semantic search / embeddings.
- Complex admin UI.
- Multi-tenant auth.
- CRM integration.
- Production hardening.
- React or a heavy frontend.
- Queues, microservices, or complex auth.
- Full analytics product or separate Contact Tracker / Trend Pulse products.

## Current product conventions

- **Default scrape/ingest window:** last 24 hours only.
  - Older posts should be filtered out by default even if Apify returns them.
  - Backfills can be explicit exceptions, not the default daily cycle.
- **Dashboard recent-post review window:** show recent saved posts from the last 7 days so Tony has something to review.
- **Daily report window:** last 24 hours.
- **Fetch UX:** use a step-by-step recap log rather than live progress.
- **Notifications:** eventually notify only when new posts are found; avoid no-post notifications except during testing.
- **AI provider:** no real AI provider for v0 unless Tony intentionally adds one; use mock/no-op report generation by default.
- **Tracked starter profiles:**
  - Arthur Brooks — `https://www.linkedin.com/in/arthur-c-brooks/`
  - Daniel Pink — `https://www.linkedin.com/in/danielpink/`
  - Dharmesh Shah — `https://www.linkedin.com/in/dharmesh/`

## Architecture principles

Keep provider-specific scraping code isolated:

```text
app/sources/
  base.py      # provider-neutral interfaces and normalized schemas
  apify.py     # Apify-specific logic
  mock.py      # fixture/mock data for tests and blocked API sessions
```

The rest of the app should consume normalized post objects, not raw Apify records.

Core flow:

```text
Tracked profiles
  -> Apify/manual/mock source adapter
  -> normalized PostInput records
  -> ingestion service with duplicate skipping
  -> SQLite posts/people/scrape_runs tables
  -> dashboard + daily report
```

## Data source notes

- Apify is the first data source.
- Actor ID currently used in local project context: `Wpp1BZ6yGWjySadk3`.
- Prefer measured, guarded real-data runs before scheduling anything.
- Guardrails should include profile count, limit per source, and a max Apify charge.
- The first real spike proved Apify can return usable fields:
  - `text`
  - `authorName`
  - `authorProfileUrl`
  - `inputUrl`
  - `url`
  - `postedAtISO`
  - `postedAtTimestamp`
  - `urn`
  - `shareUrn`
  - engagement fields like `numLikes`, `numComments`, `numShares`

## Development workflow

- Use feature branches.
- Prefer small commits.
- Keep commits teachable and reviewable.
- Run tests and lint before reporting completion.
- Use `uv run` if the environment is already set up that way; otherwise the venv commands in `README.md` are acceptable.
- Do not commit `.env` or secrets.
- Do not introduce large rewrites unless the current increment requires it.

Common verification commands:

```bash
uv run pytest -q
uv run ruff check .
```

or, with an activated venv:

```bash
pytest -q
ruff check .
```

## Current known state as of 2026-05-22

The project has moved beyond the initial foundation. The dashboard and Apify flow have working pieces.

Implemented so far:

- FastAPI app shell.
- `/health` endpoint.
- `/dashboard` route.
- SQLAlchemy database setup.
- Provider-neutral models and schemas.
- Apify spike helper and fixture.
- Apify parser into normalized post inputs.
- Ingestion service with duplicate skipping.
- Tracked profile service and profile creation API.
- Mock daily report generator and report route.
- Dashboard sections for tracked profiles, recent posts, and latest report.
- Guarded manual Apify fetch CLI/service.
- Dashboard fetch action with clearer control loop.
- Seed script for the three starter profiles.
- Real 72-hour Apify fetch was run once to populate data for review.
- Dashboard was reorganized around:
  1. Priority feed.
  2. People we follow.
  3. Profile administration placeholder.
  4. Daily report.

Latest known relevant commit from prior session:

```text
d9edb02 Reorganize dashboard around recent posts
```

Latest known verification from prior session:

```text
uv run pytest -q      # 45 passed
uv run ruff check .   # All checks passed
```

The local database after the real 72-hour fetch had:

```text
people: 3
posts: 10
scrape_runs: 1
```

## Current review focus

Tony should review the dashboard reading experience:

- Are recent posts prominent enough?
- Are post hooks/previews useful?
- Are the profile blurbs good enough for now?
- Does the page flow make sense: recent posts -> people followed -> admin?

Recommended next development focus:

1. Tighten visual layout and post-card readability.
2. Decide whether first 2–3 lines are enough for previews or whether true AI summaries are needed later.
3. Do not add archive/delete/profile management until the main feed experience feels right.

## Documentation maintenance rule

As the project evolves, append updates rather than relying only on chat history.

- Update this `AGENTS.md` when agent-facing context, conventions, workflow, architecture, or current state changes.
- Update `README.md` when human setup, usage, review instructions, or user-facing project status changes.
- Keep the two documents intentionally overlapping where useful:
  - `AGENTS.md` is the agent handoff/context file.
  - `README.md` is the human-facing setup and usage file.

## Progress log

### 2026-05-22 — Context documentation added

- Created this `AGENTS.md` to preserve cross-session project context.
- README should remain the human-facing setup/usage document.
- Future meaningful progress should be appended here and, when relevant, summarized in `README.md`.
