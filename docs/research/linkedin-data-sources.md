# LinkedIn Post Data Source Research

**Purpose:** Choose a reliable source for profile-specific LinkedIn posts before scheduling repeated checks.

## Current constraints

- Monitor only a small curated active profile list.
- Initial seed profiles: Arthur Brooks, Daniel Pink, Dharmesh Shah.
- Manual runs first; no scheduler until cost/reliability is measured.
- Prefer reliability and flexibility over lowest possible cost.
- Notify only when new posts exist once scheduling is added.

## Reddit/user-report signal

Reddit search produced general scraping discussions but no strong, current consensus that a specific provider is definitively best for LinkedIn profile-post monitoring. Useful themes from the search results:

- LinkedIn is treated as a hard scraping target.
- Reliability matters more than raw price for this use case.
- Providers can break or degrade, so we should keep the data-source layer swappable.
- Final source choice should be validated with controlled real runs, not marketing claims alone.

## Apify Store candidates found

### 1. `supreme_coder/linkedin-post` — current actor

- Title: `Linkedin Post Scraper ✅ No cookies · $1 per 1k`
- Actor ID in project: `Wpp1BZ6yGWjySadk3`
- Recent Apify store stats observed:
  - very high total runs and users
  - 30-day success count much higher than failure/time-out count
  - high review rating
- Pricing observed from actor metadata:
  - actor start event: about `$0.002`
  - post event: about `$0.001` per scraped post
- Known input from spike:
  - `urls`
  - `limitPerSource`
  - `deepScrape`
  - `rawData`
- Fit:
  - Good first manual-run candidate because it is already configured and cheap.
- Risk:
  - Need to confirm whether it supports actor-side date filtering. If not, we must limit results per profile and filter locally.

### 2. `harvestapi/linkedin-profile-posts`

- Title: `LinkedIn Profile Posts Scraper (No Cookies)`
- Recent Apify store stats observed:
  - very high total runs/users
  - extremely low failure count relative to successful 30-day runs
  - high review rating
- Pricing observed:
  - post event around `$0.002`
  - 0-result query event around `$0.001`
  - actor start event around `$0.00005`
- Fit:
  - Strong alternative candidate if current actor output is poor or unreliable.
  - Explicitly profile-post focused.
- Risk:
  - May charge for 0-result queries; this is acceptable if reliability is higher, but should be measured.

### 3. `harvestapi/linkedin-post-search`

- Title: `Linkedin Post Search Scraper (No Cookies)`
- Recent Apify store stats observed:
  - high total runs/users
  - very low failure count relative to successful 30-day runs
  - high review rating
- Pricing observed:
  - post event around `$0.002`
  - 0-result query around `$0.001`
  - optional profile/comment/reaction enrichment can add cost
- Fit:
  - Good candidate if it supports better query/date/profile filters than profile-post actors.
- Risk:
  - Search-style results may be less exact than profile-specific latest-post retrieval unless inputs constrain author/profile strongly.

### 4. Lower-volume alternatives

Examples found: `datadoping/linkedin-profile-posts-scraper`, `unseenuser/LinkedIn-Content`, and others.

- Some have attractive pricing or feature claims.
- Most have lower usage/review signal than the two high-volume candidates above.
- Keep as backup options, not first choice.

## Recommendation

Use a two-candidate validation approach:

1. Run the current configured actor first because it is already integrated and appears cheap.
2. If output quality, date filtering, or reliability is weak, test `harvestapi/linkedin-profile-posts` next.
3. Keep provider code swappable so we are not locked into one actor.

## First manual-run defaults

- max profiles: `3`
- profiles:
  - `https://www.linkedin.com/in/arthur-c-brooks/`
  - `https://www.linkedin.com/in/danielpink/`
  - `https://www.linkedin.com/in/dharmesh/`
- `limitPerSource`: `3`
- `maxTotalChargeUsd`: `$1.00`
- local lookback: `24 hours` for first test, then consider `4 hours` once scheduler exists
- no notification for no-post runs outside testing

## What to inspect after a run

- Apify run status.
- Actual charged amount if available in run metadata.
- Charged event counts if available.
- Dataset item count.
- Number of items rejected locally as old/unparseable.
- Number of new posts inserted after dedupe.
- Whether each item includes a stable post ID, timestamp, text, author, and direct URL.
