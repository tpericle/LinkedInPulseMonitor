# Manual Apify Run — 2026-05-21

## Configuration

- Actor: `supreme_coder/linkedin-post` / `Wpp1BZ6yGWjySadk3`
- Profiles:
  - Arthur Brooks
  - Daniel Pink
  - Dharmesh Shah
- `limitPerSource`: `3`
- `maxTotalChargeUsd`: `$1.00`
- Run mode: manual
- Local filter: recent items within 24 hours

## Result

- Run ID: `iSzE7XncCXdYPMJvJ`
- Dataset ID: `pZdZK2OxFpqSgSM4X`
- Status: `SUCCEEDED`
- Runtime: about 6 seconds
- Actual usage: `$0.011`
- Charged events:
  - actor start: `1`
  - posts scraped: `9`
- Recent dataset items saved locally: `5`

## What this means

- The actor appears inexpensive for this small three-profile run.
- The charge was for 9 scraped posts, not only the 5 locally recent items we kept.
- Local filtering is still necessary, but cost should be estimated from actor-returned/scraped items, not only final useful posts.
- With `limitPerSource: 3`, this run cost roughly 1.1 cents.

## Data quality observations

- Returned stable post identifiers via `shareUrn`/`urn`.
- Returned direct LinkedIn post URLs.
- Returned author names/profile URLs.
- Returned timestamps.
- Returned post text.
- Recent returned posts came from Daniel Pink and Arthur Brooks; none from Dharmesh Shah in the local 24-hour filter.

## Recommendation from this run

Continue with the current actor for the first guarded manual-fetch integration.

Initial guardrails remain reasonable:

- manual only
- max 3 active profiles
- `limitPerSource: 3`
- `maxTotalChargeUsd: 1.00`
- local 24-hour filter while validating
- later use a 4-hour filter/scheduler once the manual path is trusted
- notify only when new posts are found after scheduling

## Follow-up

The spike script now supports `--limit-per-source` and refetches run details after completion so the cost summary reflects final charged event counts.
