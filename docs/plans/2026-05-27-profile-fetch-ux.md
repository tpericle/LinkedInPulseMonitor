# Profile Management and Fetch UX Implementation Plan

> **For Hermes:** Use test-driven-development for each behavior change.

**Goal:** Make active profile management and the manual fetch flow understandable for Tony as a user.

**Architecture:** Keep the app local-first and simple. Reuse the existing FastAPI dashboard router, SQLAlchemy models, and Apify manual fetch service. Avoid a new migration by determining "new profile" status from whether a successful scrape run happened after the profile was added.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy, pytest, ruff.

---

## Task 1: Dashboard copy and profile form simplification

- Rename the feed heading to `Activity from the last 7 days`.
- Remove company/tags from the visible add-profile form.
- Keep database fields for compatibility, but stop using them in the dashboard UI.
- Update tests that assert dashboard copy and form fields.

## Task 2: Active profile limit

- Set max active profile limit to 10.
- If adding/reactivating would create an 11th active profile, refuse with a clear dashboard error.
- Keep paused profiles allowed beyond 10, but they are not included in fetches.
- Add tests for add/reactivate limit handling.

## Task 3: Edit, pause, reactivate, and delete profile actions

- Add edit support for display name and LinkedIn URL.
- Rename Archive to Pause tracking.
- Add delete only for paused profiles.
- Delete profile record only; keep historical posts by setting `Post.person_id = None` first.
- Add tests for edit, pause labels, delete guard, and paused delete behavior.

## Task 4: Two-step fetch confirmation

- Change dashboard fetch button to a GET confirmation page/section.
- Confirmation shows: active profiles, normal 24-hour lookback, new-profile 7-day initial lookback, per-profile limit, max Apify charge, duplicate/out-of-window skip behavior.
- Execute button POSTs to the real fetch endpoint.
- Add tests for visible confirmation and active profile list.

## Task 5: New-profile 7-day first fetch

- New profile means: no successful Apify scrape run has happened after `Person.added_at`.
- Dashboard fetch partitions profiles:
  - existing profiles: 24-hour lookback
  - new profiles: 7-day initial lookback
- Run separate guarded Apify fetches for each group when both exist.
- Keep CLI daily/manual fetch behavior compatible.
- Add service tests for custom profile subsets and dashboard fetch orchestration.

## Task 6: Detailed fetch result recap

- Show checked profiles, returned items, parsed posts, saved posts, skipped posts, status, cost.
- Explain that zero new saved posts is not an error.
- Include likely skip reasons: already saved, outside lookback, invalid/unparseable.
- Add tests for the new recap text.

## Task 7: Documentation and verification

- Update README and AGENTS current status/review focus.
- Run `uv run pytest -q` and `uv run ruff check .`.
