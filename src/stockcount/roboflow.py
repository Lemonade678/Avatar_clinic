"""Ask a Roboflow hosted model what packaging it sees in a shelf photo (US-hosted — within the ≤5 countries)."""
from __future__ import annotations

import base64

import httpx

from .cv import CvUnavailable

# ⚠️ Roboflow's hosted detection endpoint; newer accounts may be shown "https://serverless.roboflow.com".
# Override with ROBOFLOW_API_URL if the dashboard shows a different one.
DEFAULT_URL = "https://detect.roboflow.com"


class RoboflowClient:
    def __init__(self, model: str, api_key: str, base_url: str = DEFAULT_URL,
                 client: httpx.Client | None = None, timeout: float = 10.0):
        self.model = model.strip("/")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)

    def predict(self, image: bytes) -> list[dict]:
        """[{"class": "bottle", "confidence": 0.93}, ...] or CvUnavailable. Errors never include the key."""
        try:
            r = self.client.post(
                f"{self.base_url}/{self.model}",
                params={"api_key": self.api_key},
                content=base64.b64encode(image),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as e:
            raise CvUnavailable(f"Roboflow unreachable ({e.__class__.__name__})") from None
        if r.status_code != 200:
            raise CvUnavailable(f"Roboflow answered HTTP {r.status_code}")
        predictions = r.json().get("predictions")
        if not isinstance(predictions, list):
            raise CvUnavailable("unexpected Roboflow response")
        return [{"class": p.get("class"), "confidence": float(p.get("confidence", 0))} for p in predictions]
