# Manual Apify Cost Inspection Runbook

Use this before any scheduled LinkedIn checks.

## Goal

Run one small real-data scrape, then inspect actual cost and output quality before deciding guardrails.

## Defaults for the first run

- Profiles: Arthur Brooks, Daniel Pink, Dharmesh Shah.
- Max profiles: `3`.
- `limitPerSource`: `3`.
- `maxTotalChargeUsd`: `1.00`.
- Manual run only.
- Local lookback: `24 hours` for first validation.

## Commands

Inspect actor metadata without running a scrape:

```bash
source .venv/bin/activate
python scripts/apify_spike.py --inspect
```

Run the controlled scrape:

```bash
source .venv/bin/activate
python scripts/apify_spike.py --run --input-key urls --limit-per-source 3 --max-total-charge-usd 1.00
```

## What Tony should check in Apify Console

After the run, open the Apify run detail page and check:

- Run status.
- Usage / charge amount.
- Charged events, especially post count and actor-start event.
- Dataset item count.
- Whether items match the three target people.
- Whether direct post URLs work.

## What the app should report locally

- profiles requested
- item limit per profile
- run ID
- run status
- default dataset ID
- actual usage/charge fields if Apify returns them
- dataset items returned
- recent items saved to fixture

## Decision after first run

If output is good and cost is low:

- keep current actor for guarded manual fetch integration
- later schedule every 4 hours

If output is stale, incomplete, or unreliable:

- test `harvestapi/linkedin-profile-posts`
- compare output and cost using the same three profiles and same run cap

## Notification policy

During manual testing: print/report no-post results.

After scheduling: do not notify Tony for no-post runs. Notify only when new posts are found.
