# Fixture notes

`apify_sample_posts.json` is a small sanitized development fixture from the initial Apify spike.

The full Apify run returned hundreds of records, but this fixture intentionally keeps only a few records per input profile so the repo stays lightweight and reviewable.

Initial spike profiles:

- https://www.linkedin.com/in/arthur-c-brooks/
- https://www.linkedin.com/in/danielpink/
- https://www.linkedin.com/in/dharmesh/

Observed useful fields include:

- `urn`
- `shareUrn`
- `url`
- `inputUrl`
- `authorName`
- `authorProfileUrl`
- `authorProfileId`
- `text`
- `postedAtISO`
- `postedAtTimestamp`
- `numLikes`
- `numComments`
- `numShares`
- `comments`
- `reactions`
