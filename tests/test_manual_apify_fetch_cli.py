from app.manual_fetch import ManualFetchResult
from scripts.manual_apify_fetch import format_fetch_result


def test_format_fetch_result_reports_guardrail_and_cost_counts():
    message = format_fetch_result(
        ManualFetchResult(
            profiles_checked=3,
            items_returned=9,
            parsed_count=5,
            inserted_count=4,
            skipped_count=5,
            provider_run_id="run-123",
            provider_dataset_id="dataset-123",
            status="SUCCEEDED",
            usage_total_usd=0.011,
            charged_event_counts={"actor-start-gb": 1, "post": 9},
        )
    )

    assert "profiles checked: 3" in message
    assert "items returned: 9" in message
    assert "new posts inserted: 4" in message
    assert "skipped items/posts: 5" in message
    assert "usage total USD: 0.011" in message
    assert "charged events: {'actor-start-gb': 1, 'post': 9}" in message
