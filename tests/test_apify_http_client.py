import httpx

from app.apify_http import ApifyHttpClient


def test_apify_http_client_runs_actor_with_cost_cap_and_fetches_results():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v2/acts/actor-123/runs":
            assert request.url.params["waitForFinish"] == "180"
            assert request.url.params["maxTotalChargeUsd"] == "1.0"
            assert request.headers["authorization"] == "Bearer token-123"
            assert request.read() == b'{"urls":["https://www.linkedin.com/in/dharmesh/"]}'
            return httpx.Response(200, json={"data": {"id": "run-123"}})
        if request.url.path == "/v2/datasets/dataset-123/items":
            assert request.url.params["clean"] == "true"
            assert request.url.params["format"] == "json"
            return httpx.Response(200, json=[{"id": "post-1"}])
        if request.url.path == "/v2/actor-runs/run-123":
            return httpx.Response(200, json={"data": {"usageTotalUsd": 0.011}})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    http_client = httpx.Client(
        base_url="https://api.apify.com/v2",
        transport=httpx.MockTransport(handler),
    )
    client = ApifyHttpClient(token="token-123", http_client=http_client)

    run = client.run_actor(
        "actor-123",
        {"urls": ["https://www.linkedin.com/in/dharmesh/"]},
        1.0,
    )
    items = client.fetch_dataset_items("dataset-123")
    details = client.fetch_run_details("run-123")

    assert run == {"id": "run-123"}
    assert items == [{"id": "post-1"}]
    assert details == {"usageTotalUsd": 0.011}
    assert [request.method for request in requests] == ["POST", "GET", "GET"]
