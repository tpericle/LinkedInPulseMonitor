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

## Verdict: PENDING

### What worked

- Local `.env` exists.
- `APIFY_TOKEN` is present locally.
- `APIFY_ACTOR_ID` is set to `Wpp1BZ6yGWjySadk3`.
- The actor metadata is reachable through the Apify API.

### What is not proven yet

- The exact actor input field name for profile URLs.
- Whether this actor returns profile posts from the three URLs.
- Whether returned items include content, author/profile URL, post URL, timestamp, and a stable unique ID.

### Recommendation for the real build

Before writing `app/sources/apify.py`, confirm the actor input shape in Apify Console and run the helper once. Then build the parser against the saved fixture instead of guessing from docs.
