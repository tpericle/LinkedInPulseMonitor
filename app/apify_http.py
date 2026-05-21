from __future__ import annotations

from typing import Any

import httpx

APIFY_API_BASE = "https://api.apify.com/v2"


class ApifyHttpClient:
    def __init__(self, *, token: str, http_client: httpx.Client | None = None) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=APIFY_API_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=180,
        )
        if http_client is not None:
            self._client.headers.update({"Authorization": f"Bearer {token}"})

    def __enter__(self) -> ApifyHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def run_actor(
        self,
        actor_id: str,
        actor_input: dict[str, Any],
        max_total_charge_usd: float,
    ) -> dict[str, Any]:
        response = self._client.post(
            f"/acts/{actor_id}/runs",
            params={"waitForFinish": 180, "maxTotalChargeUsd": max_total_charge_usd},
            json=actor_input,
        )
        response.raise_for_status()
        return response.json()["data"]

    def fetch_dataset_items(self, dataset_id: str) -> list[dict[str, Any]]:
        response = self._client.get(
            f"/datasets/{dataset_id}/items",
            params={"clean": "true", "format": "json"},
        )
        response.raise_for_status()
        return response.json()

    def fetch_run_details(self, run_id: str) -> dict[str, Any]:
        response = self._client.get(f"/actor-runs/{run_id}")
        response.raise_for_status()
        return response.json()["data"]
