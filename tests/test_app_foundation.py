from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db import Base, get_db
from app.main import app
from app.manual_fetch import ManualFetchResult
from app.models import DailyReport, Person, Post, ScrapeRun
from app.sample_profiles import SAMPLE_PROFILES, seed_sample_profiles


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client_with_db(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_reports_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_renders_project_name():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "LinkedIn Pulse Monitor" in response.text


def test_dashboard_renders_profile_administration_form():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Profile administration" in response.text
    assert "Add a tracked LinkedIn profile" in response.text
    assert 'action="/dashboard/profiles"' in response.text
    assert 'name="linkedin_url"' in response.text
    assert 'name="full_name"' in response.text
    assert 'name="company"' in response.text


def test_seed_sample_profiles_creates_three_active_starter_profiles(db_session: Session):
    seeded_ids = seed_sample_profiles(db_session)

    people = db_session.scalars(select(Person).order_by(Person.full_name)).all()
    assert len(seeded_ids) == 3
    assert {person.full_name for person in people} == {
        profile.full_name for profile in SAMPLE_PROFILES
    }
    assert all(person.is_active for person in people)
    assert all(person.company for person in people)


def test_dashboard_renders_recent_posts_and_latest_report(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Post(
            source="apify",
            source_post_id="post-1",
            author_name="Recent Author",
            content=(
                "Line one hook.\nLine two hook.\nLine three hook.\nLine four should not appear."
            ),
            post_type="post",
            authored_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3),
            raw_json="{}",
        )
    )
    db_session.add(
        DailyReport(
            report_date=date(2026, 5, 20),
            post_count=1,
            summary_text="Dashboard should show this report.",
            themes_json="[]",
            notable_posts_json="[]",
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Recent Author" in response.text
    assert "Review today" in response.text
    assert "~3h ago" in response.text
    assert "Line one hook." in response.text
    assert "Line two hook." in response.text
    assert "Line three hook." in response.text
    assert "Line four should not appear." not in response.text
    assert "Dashboard should show this report." in response.text


def test_dashboard_renders_active_profiles_and_hides_inactive_profiles(
    db_session: Session, client_with_db: TestClient
):
    db_session.add_all(
        [
            Person(
                full_name="Dr. Arthur Brooks",
                company="Harvard",
                linkedin_url="https://www.linkedin.com/in/arthur-c-brooks/",
                is_active=True,
            ),
            Person(
                full_name="Archived Person",
                company="Old Company",
                linkedin_url="https://www.linkedin.com/in/archived-person/",
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "People we follow" in response.text
    assert "These are the people that we’re following" in response.text
    assert "1 active profile configured" in response.text
    assert "Dr. Arthur Brooks" in response.text
    assert "Harvard" in response.text
    assert "https://www.linkedin.com/in/arthur-c-brooks/" in response.text
    assert "Archived profiles" in response.text
    assert "Archived Person" in response.text
    assert "Reactivate" in response.text


def test_dashboard_explains_when_no_active_profiles(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Person(
            full_name="Inactive Only",
            linkedin_url="https://www.linkedin.com/in/inactive-only/",
            is_active=False,
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "No active profiles configured" in response.text
    assert "Manual fetch needs at least one active profile before it can run." in response.text


def test_dashboard_profile_form_creates_profile_redirects_to_admin_and_confirms(
    db_session: Session, client_with_db: TestClient
):
    response = client_with_db.post(
        "/dashboard/profiles",
        data={
            "linkedin_url": "https://www.linkedin.com/in/dharmesh",
            "full_name": "Dharmesh Shah",
            "company": "HubSpot",
            "tags": "startup, marketing",
        },
        follow_redirects=False,
    )

    stored_person = db_session.scalars(select(Person)).one()
    assert response.status_code == 303
    assert response.headers["location"] == (
        "/dashboard?success=Added+Dharmesh+Shah+to+active+profiles"
        "#profile-administration"
    )
    assert stored_person.linkedin_url == "https://www.linkedin.com/in/dharmesh/"
    assert stored_person.full_name == "Dharmesh Shah"
    assert stored_person.company == "HubSpot"
    assert stored_person.tags_json == '["startup", "marketing"]'

    refreshed = client_with_db.get(response.headers["location"])
    assert refreshed.status_code == 200
    assert "Added Dharmesh Shah to active profiles" in refreshed.text
    assert "Profile administration" in refreshed.text
    assert "Dharmesh Shah" in refreshed.text
    assert "HubSpot" in refreshed.text
    assert "1 active profile configured" in refreshed.text


def test_dashboard_profiles_get_redirects_to_administration(client_with_db: TestClient):
    response = client_with_db.get("/dashboard/profiles", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard#profile-administration"


def test_dashboard_profile_form_guides_invalid_linkedin_url(
    db_session: Session, client_with_db: TestClient
):
    response = client_with_db.post(
        "/dashboard/profiles",
        data={"linkedin_url": "https://example.com/not-linkedin"},
    )

    assert response.status_code == 400
    assert db_session.scalars(select(Person)).all() == []
    assert "Please enter a LinkedIn profile URL" in response.text
    assert "https://www.linkedin.com/in/" in response.text


def test_dashboard_archive_profile_deactivates_profile_and_confirms(
    db_session: Session, client_with_db: TestClient
):
    person = Person(
        full_name="Archive Me",
        linkedin_url="https://www.linkedin.com/in/archive-me/",
        is_active=True,
    )
    db_session.add(person)
    db_session.commit()

    response = client_with_db.post(
        f"/dashboard/profiles/{person.id}/archive", follow_redirects=False
    )

    db_session.refresh(person)
    assert response.status_code == 303
    assert response.headers["location"] == (
        "/dashboard?success=Archived+Archive+Me.+They+will+not+be+included+in+future+fetches."
        "#profile-administration"
    )
    assert person.is_active is False

    refreshed = client_with_db.get(response.headers["location"])
    assert refreshed.status_code == 200
    assert "Archived Archive Me. They will not be included in future fetches." in refreshed.text
    assert "Archived profiles" in refreshed.text
    assert "Archive Me" in refreshed.text
    assert "Reactivate" in refreshed.text


def test_dashboard_reactivate_profile_activates_profile_and_confirms(
    db_session: Session, client_with_db: TestClient
):
    person = Person(
        full_name="Reactivate Me",
        linkedin_url="https://www.linkedin.com/in/reactivate-me/",
        is_active=False,
    )
    db_session.add(person)
    db_session.commit()

    response = client_with_db.post(
        f"/dashboard/profiles/{person.id}/reactivate", follow_redirects=False
    )

    db_session.refresh(person)
    assert response.status_code == 303
    assert response.headers["location"] == (
        "/dashboard?success=Reactivated+Reactivate+Me.+They+will+be+included+in+future+fetches."
        "#profile-administration"
    )
    assert person.is_active is True

    refreshed = client_with_db.get(response.headers["location"])
    assert refreshed.status_code == 200
    assert "Reactivated Reactivate Me. They will be included in future fetches." in refreshed.text
    assert "Reactivate Me" in refreshed.text
    assert "Archive" in refreshed.text


def test_dashboard_admin_actions_use_confirmation_prompts(
    db_session: Session, client_with_db: TestClient
):
    db_session.add_all(
        [
            Person(
                full_name="Active Person",
                linkedin_url="https://www.linkedin.com/in/active-person/",
                is_active=True,
            ),
            Person(
                full_name="Inactive Person",
                linkedin_url="https://www.linkedin.com/in/inactive-person/",
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert 'id="profile-administration"' in response.text
    archive_confirm = (
        "return confirm('Archive this profile? "
        "It will stop appearing in future fetches.');"
    )
    reactivate_confirm = (
        "return confirm('Reactivate this profile? It will be included in future fetches.');"
    )
    assert archive_confirm in response.text
    assert reactivate_confirm in response.text


def test_dashboard_manual_fetch_button_renders_guarded_fetch_button():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Fetch latest posts now" in response.text
    assert "action=\"/dashboard/fetch/apify\"" in response.text


def test_dashboard_orders_recent_posts_then_followed_people_then_administration():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    recent_index = response.text.index("Priority feed")
    people_index = response.text.index("People we follow")
    admin_index = response.text.index("Profile administration")
    assert recent_index < people_index < admin_index


def test_dashboard_recent_posts_focuses_on_last_seven_days(
    db_session: Session, client_with_db: TestClient
):
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add_all(
        [
            Post(
                source="apify",
                source_post_id="recent-seven-day-post",
                author_name="Seven Day Author",
                content="This post is inside the seven day dashboard window.",
                post_type="post",
                authored_at=now - timedelta(days=6),
                linkedin_url="https://www.linkedin.com/feed/update/urn:li:share:recent-seven-day-post/",
                raw_json="{}",
            ),
            Post(
                source="apify",
                source_post_id="older-than-seven-days",
                author_name="Old Author",
                content="This post should not be shown on the dashboard.",
                post_type="post",
                authored_at=now - timedelta(days=8),
                raw_json="{}",
            ),
        ]
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Recent posts from the last 7 days" in response.text
    assert "Seven Day Author" in response.text
    assert "Review window" in response.text
    assert "~6d ago" in response.text
    assert "This post is inside the seven day dashboard window." in response.text
    post_url = "https://www.linkedin.com/feed/update/urn:li:share:recent-seven-day-post/"
    assert post_url in response.text
    assert "Open post →" in response.text
    assert "Old Author" not in response.text
    assert "This post should not be shown on the dashboard." not in response.text


def test_dashboard_empty_recent_posts_names_seven_day_window_and_last_fetch(
    db_session: Session, client_with_db: TestClient
):
    last_fetch = datetime(2026, 5, 21, 15, 30)
    db_session.add(
        ScrapeRun(
            provider="apify",
            status="SUCCEEDED",
            started_at=last_fetch,
            finished_at=last_fetch,
            item_count=0,
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Nothing posted in the last 7 days." in response.text
    assert "Last fetch: 2026-05-21 15:30" in response.text


def test_dashboard_manual_fetch_button_runs_guarded_fetch_and_shows_step_log(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    client_with_db: TestClient,
):
    db_session.add(
        Person(
            full_name="Dharmesh Shah",
            linkedin_url="https://www.linkedin.com/in/dharmesh/",
            is_active=True,
        )
    )
    db_session.commit()
    calls = []

    def fake_run_dashboard_manual_fetch(db: Session) -> ManualFetchResult:
        calls.append(db)
        return ManualFetchResult(
            profiles_checked=1,
            items_returned=3,
            parsed_count=2,
            inserted_count=1,
            skipped_count=2,
            provider_run_id="run-123",
            provider_dataset_id="dataset-123",
            status="SUCCEEDED",
            usage_total_usd=0.011,
            charged_event_counts={"post": 3},
        )

    monkeypatch.setattr(
        "app.routers.dashboard._run_dashboard_manual_fetch",
        fake_run_dashboard_manual_fetch,
    )

    response = client_with_db.post("/dashboard/fetch/apify", follow_redirects=True)

    assert response.status_code == 200
    assert calls == [db_session]
    assert "Fetch recap" in response.text
    assert "Found 1 active profile." in response.text
    assert "Asked Apify for up to 3 latest posts per profile." in response.text
    assert "Apify returned 3 items." in response.text
    assert "Parsed 2 posts from those items." in response.text
    assert "Saved 1 new post and skipped 2 existing or out-of-window posts." in response.text
    assert "Provider status: SUCCEEDED." in response.text
    assert "Estimated Apify cost: $0.011." in response.text


def test_dashboard_daily_report_button_generates_report(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Post(
            source="apify",
            source_post_id="post-for-report",
            author_name="Report Author",
            content="Dashboard action should include this post in the report.",
            post_type="post",
            authored_at=datetime.now(UTC).replace(tzinfo=None),
            raw_json="{}",
        )
    )
    db_session.commit()

    response = client_with_db.post("/dashboard/reports/daily", follow_redirects=True)

    stored_report = db_session.scalars(select(DailyReport)).one()
    assert response.status_code == 200
    assert stored_report.post_count == 1
    assert "Generated today’s mock report from 1 recent post" in response.text
    assert "Mock summary for 1 recent LinkedIn post." in response.text


def test_dashboard_recent_post_cards_show_non_copy_paste_comment_starters(
    db_session: Session, client_with_db: TestClient
):
    db_session.add(
        Post(
            source="apify",
            source_post_id="post-with-starters",
            author_name="Founder Author",
            content="AI workflows are changing how founders build with customers.",
            post_type="post",
            authored_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2),
            raw_json="{}",
        )
    )
    db_session.commit()

    response = client_with_db.get("/dashboard")

    assert response.status_code == 200
    assert "Comment starter ideas" in response.text
    assert "These are thinking prompts, not copy-paste comments." in response.text
    assert (
        "One angle Tony might explore: connect this post to AI and practical workflows."
        in response.text
    )
    assert (
        "A useful question Tony could ask: what is one practical next step "
        "or tradeoff behind this idea?"
        in response.text
    )
    assert (
        "A personal observation Tony might add: relate the post to learning "
        "in public with agent-assisted product building."
        in response.text
    )
