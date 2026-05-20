from sqlalchemy import inspect

from app.db import create_db, engine


def test_create_db_creates_foundation_tables():
    create_db()

    table_names = set(inspect(engine).get_table_names())

    assert {
        "people",
        "scrape_runs",
        "posts",
        "post_themes",
        "daily_reports",
    }.issubset(table_names)
