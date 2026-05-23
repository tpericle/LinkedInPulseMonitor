# Regular Runs, Administration, and Commentary Guidance Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn the current local dashboard into a repeatable daily/near-real-time workflow with safe profile administration and Tony-style comment recommendations.

**Architecture:** Keep the app local-first. Reuse the guarded manual Apify fetch service before introducing scheduling. Store administration state in existing `people.is_active`. Treat Tony's voice/profile as markdown source material that the app reads and uses to generate suggestions later.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Jinja2, local markdown files, Apify, mock/no-op AI first.

---

## Phase 1 — Regular guarded runs

**Outcome:** Tony can run the same guarded fetch repeatedly without using the dashboard manually every time.

### Task 1: Add a single command for the daily cycle

**Objective:** Create one CLI entry point that runs fetch, ingests new posts, and generates the mock daily report.

**Files:**
- Create: `scripts/daily_cycle.py`
- Test: `tests/test_daily_cycle.py`

**Behavior:**
- Use active profiles only.
- Keep the default lookback to 24 hours.
- Keep Apify guardrails: `limit_per_source`, `max_total_charge_usd`.
- Generate a report after fetching.
- Print a concise recap: profiles checked, items returned, parsed, inserted, skipped, cost.

### Task 2: Add a local scheduled-run option

**Objective:** Document and optionally generate a launchd plist or cron instruction for Tony's Mac.

**Files:**
- Create: `docs/runbooks/scheduled-local-run.md`

**Recommendation:**
- Start with local macOS `launchd` or a simple cron job, not cloud hosting.
- Schedule every 2-4 hours during the day once costs are acceptable.
- Notify only if `inserted_count > 0`.

### Task 3: Add no-new-post silence

**Objective:** Ensure scheduled runs stay quiet when there is nothing new.

**Files:**
- Modify: daily cycle script / notification wrapper when notifications are added.

**Behavior:**
- If no new posts are inserted, log locally but do not send a user notification.
- If new posts are inserted, send a short message with dashboard link and post count.

---

## Phase 2 — Administration and archive

**Outcome:** Tony can maintain the curated profile list without editing the database directly.

### Task 1: Basic dashboard administration

**Status:** Started on 2026-05-23.

**Implemented behavior:**
- Add a profile from the dashboard.
- Archive an active profile.
- Reactivate an archived profile.
- Archived profiles remain stored but are excluded from fetches.

### Task 2: Improve admin clarity

**Objective:** Make administration safer as the profile list grows.

**Files:**
- Modify: `app/templates/dashboard.html`
- Modify: `app/routers/dashboard.py`
- Test: `tests/test_app_foundation.py`

**Behavior:**
- Show profile counts: active and archived.
- Make archive/reactivate actions visually clear.
- Add confirmation text after each action.
- Keep hard delete out of scope unless Tony explicitly asks for it.

### Task 3: Optional edit profile details

**Objective:** Allow correcting display name, company/note, tags, or LinkedIn URL.

**Recommendation:**
- Do this only after archive/reactivate feels right.
- Keep it small: one edit form per profile or a simple detail route.

---

## Phase 3 — Tony-style commentary recommendations from markdown

**Outcome:** Tony can maintain a markdown file that describes his profile, point of view, and commentary style; the app can use it to suggest genuine comment starter ideas for each post.

### Task 1: Add a markdown voice profile file

**Objective:** Create a human-editable source file for Tony's style and perspective.

**Files:**
- Create: `docs/profile/tony-commentary-style.md`

**Suggested structure:**

```markdown
# Tony Commentary Style

## Professional identity
- Who Tony is
- What he is building
- Who he wants to engage with

## Point of view
- Beliefs about leadership, AI, entrepreneurship, marketing, sales, or work
- Topics where Tony has a distinct angle

## Commenting principles
- Be specific, not generic
- Add a genuine observation
- Ask thoughtful questions when appropriate
- Do not sound promotional
- Do not copy-paste full comments without review

## Voice examples
### Example 1
Original post topic:
Tony's possible comment:
Why this sounds like Tony:

### Example 2
...

## Avoid
- Phrases Tony would not say
- Overly polished AI-sounding comments
- Generic praise like "Great post!"
```

### Task 2: Add a markdown reader service

**Objective:** Load Tony's commentary profile from markdown so future suggestion code can use it.

**Files:**
- Create: `app/commentary_profile.py`
- Test: `tests/test_commentary_profile.py`

**Behavior:**
- Read `docs/profile/tony-commentary-style.md`.
- Return sections or raw markdown.
- If missing, return a clear setup message.

### Task 3: Mock comment starter suggestions

**Objective:** Add a local/mock suggestion section to post cards before using a real AI provider.

**Files:**
- Modify: `app/routers/dashboard.py`
- Modify: `app/templates/dashboard.html`
- Test: `tests/test_app_foundation.py`

**Behavior:**
- For each post, show 2-3 comment starter prompts.
- Make it clear these are drafts/thinking prompts, not copy-paste comments.
- Use Tony's markdown profile as context.

### Task 4: Real AI provider later

**Objective:** Once Tony likes the UX, wire in a real provider.

**Recommendation:**
- Keep provider calls behind a small interface.
- Continue mock-by-default for tests and local setup.
- Do not persist secrets in repo.
- Avoid generating final comments; generate angles/questions Tony can personalize.

---

## Recommended next order

1. Finish reviewing the basic administration section added on 2026-05-23.
2. Add the daily cycle CLI so regular runs are one command.
3. Create `docs/profile/tony-commentary-style.md` and fill it with Tony's voice examples.
4. Add mock comment starter suggestions using that markdown file.
5. Only then schedule the daily cycle and consider real AI suggestions.
