# LinkedIn Engagement Feed Plan

**Goal:** Build a small, reliable LinkedIn engagement feed for Tony that monitors a curated list of important people, finds only new posts, summarizes each post with a direct link, and helps Tony engage within a few hours.

**Product definition:** This is not a broad analytics system. It is a focused feed for people Tony intentionally follows outside the LinkedIn algorithm.

**Current seed profiles:**
- Arthur Brooks — `https://www.linkedin.com/in/arthur-c-brooks/`
- Daniel Pink — `https://www.linkedin.com/in/danielpink/`
- Dharmesh Shah — `https://www.linkedin.com/in/dharmesh/`

## Operating principles

- Manual real-data runs first; no scheduler until costs and reliability are understood.
- Use real LinkedIn/Apify data, not fake fixtures, for source validation.
- Keep guardrails close to the API call, not only after local filtering.
- Prefer a more reliable/flexible provider even if it costs more.
- Store only operational state: tracked people, active/inactive status, seen post IDs, and a short recent cache.
- Do not send no-post notifications long term; notify only when new posts are found.
- Avoid analytics unless a concrete short-lookback use case appears.

## Phase 1 — People administration and active set

**Outcome:** Tony can maintain the curated list safely.

- Add/edit/deactivate/reactivate tracked people.
- Show active vs inactive profiles.
- Ensure only active profiles are eligible for fetches.
- Keep deactivation, not hard delete.

**Tony feedback needed:** None; Tony already chose deactivation over hard delete.

## Phase 2 — Manual guarded real fetch

**Outcome:** We can run a real fetch against the three seed profiles and understand cost/reliability before automating.

- Run manually only.
- Use active profiles only.
- Start with three profiles max.
- Start with low `limitPerSource`, likely 3–5.
- Use Apify `maxTotalChargeUsd` per run.
- Capture run metadata needed for Tony to inspect real cost.
- Show counts: profiles checked, items returned, parsed posts, inserted posts, skipped duplicates/old posts.
- Filter to a recent window such as 4 or 24 hours depending on what the actor supports.

**Tony feedback needed:** After the first controlled run, Tony reviews cost and returned item quality with us.

## Phase 3 — Engagement feed

**Outcome:** Tony sees new posts worth reviewing.

- Feed shows only new/recent posts from active tracked people.
- Each item includes person, short summary, direct LinkedIn post link, timestamp/age, and source status.
- Add simple reviewed/engaged status if useful.
- No notification when there are no posts.

**Tony feedback needed:** Whether newest-first ordering is sufficient or whether important-person-first ordering is needed.

## Later phases

- Phase 4 — Comment starter ideas based on Tony’s voice and methodology.
- Phase 5 — Schedule checks every few hours and notify only when new posts appear.
- Phase 6 — Lightweight refinement from Tony’s feedback on useful posts/comment angles.

## Data-source research note

The current Apify actor is only the first candidate. Before committing to long-term scheduling, compare available LinkedIn post data sources for:

- reliability and freshness
- profile-specific post retrieval
- date/time filtering support
- result limits per profile
- cost model and charge visibility
- output quality: direct post URL, post text, author, timestamp, stable ID
- operational safety: hard run cost caps, retries, error transparency

Reddit and user reports can be useful signal, but final choice should be validated with a small controlled real run and measured output/cost.
