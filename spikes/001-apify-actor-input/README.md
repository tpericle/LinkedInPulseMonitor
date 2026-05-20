# Spike 001: Apify actor input and dataset shape

## Question

Given Tony's selected Apify actor and three LinkedIn profile URLs, can we run the actor and get usable post data for the parser?

## Profiles

- https://www.linkedin.com/in/arthur-c-brooks/
- https://www.linkedin.com/in/danielpink/
- https://www.linkedin.com/in/dharmesh/

## Actor

- Actor ID: `Wpp1BZ6yGWjySadk3`
- Store title observed through the Apify API: `Linkedin Post Scraper ✅ No cookies · $1 per 1k`

## Current helper

Created a lightweight script:

```bash
python scripts/apify_spike.py --inspect
```

It verifies local `.env` configuration, fetches actor metadata, and prints the candidate input payload without printing secrets.

To run the paid scrape later:

```bash
python scripts/apify_spike.py --run --input-key urls
```

If Apify Console shows the profile-list field has a different name, replace `urls`:

```bash
python scripts/apify_spike.py --run --input-key <field_name_from_apify>
```

The script saves dataset output to:

```text
tests/fixtures/apify_sample_posts.json
```

## Verdict: VALIDATED

### What worked

- Local `.env` exists.
- `APIFY_TOKEN` is present locally.
- `APIFY_ACTOR_ID` is set to `Wpp1BZ6yGWjySadk3`.
- The actor metadata is reachable through the Apify API.
- Apify Console JSON confirmed the profile/source list key is `urls`.
- The actor returned records for all three profile URLs.
- The result includes the core parser fields we need:
  - `text`
  - `authorName`
  - `authorProfileUrl`
  - `inputUrl`
  - `url`
  - `postedAtISO`
  - `urn`
  - `shareUrn`
  - `postedAtTimestamp`

### Surprises

- The run produced far more data than expected even though the script only sent three profile URLs.
- The helper passed a cost cap, but the actor run still needed to be manually aborted after enough data was collected.
- The full dataset was too large for a teaching fixture, so it was reduced to a small representative sample before committing.

### Recommendation for the real build

Build `app/sources/apify.py` against the saved fixture using `urn` as the first-choice stable ID, falling back to `shareUrn`, then `url`, then a deterministic hash from `inputUrl + text + postedAtISO`.
