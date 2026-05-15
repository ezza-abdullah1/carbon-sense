"""
N8nClient — thin HTTP wrapper around the n8n workflow webhooks.

Two webhooks are expected on the n8n side:
  POST {N8N_WEBHOOK_BASE}/generate-recs   → returns the recommendation payload
  POST {N8N_WEBHOOK_BASE}/feedback        → records anonymous user feedback

Both routes require the `X-Carbonsense-Token` header to match
`settings.N8N_SHARED_SECRET`.
"""

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class N8nUnavailable(RuntimeError):
    """Raised when n8n cannot be reached or returns a non-2xx response."""


class N8nClient:
    """Thin client. No retries — callers decide how to fall back."""

    def __init__(self) -> None:
        self.base = (settings.N8N_WEBHOOK_BASE or "").rstrip("/")
        self.token = settings.N8N_SHARED_SECRET
        self.timeout = settings.N8N_TIMEOUT_SECONDS

    @property
    def configured(self) -> bool:
        return bool(self.base and self.token)

    def _post(self, path: str, payload: dict[str, Any], timeout: int | None = None) -> dict:
        if not self.configured:
            raise N8nUnavailable("N8N_WEBHOOK_BASE or N8N_SHARED_SECRET not set")

        url = f"{self.base}/{path.lstrip('/')}"
        try:
            r = requests.post(
                url,
                json=payload,
                headers={
                    "X-Carbonsense-Token": self.token,
                    "Content-Type": "application/json",
                },
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as e:
            raise N8nUnavailable(f"n8n network error: {e}") from e

        if r.status_code >= 400:
            raise N8nUnavailable(
                f"n8n returned {r.status_code}: {r.text[:200]}"
            )

        try:
            return r.json()
        except ValueError as e:
            raise N8nUnavailable(f"n8n returned non-JSON body: {e}") from e

    def generate(self, payload: dict[str, Any]) -> dict:
        """Call the generate-recs workflow and return its parsed JSON response."""
        return self._post("generate-recs", payload)

    def submit_feedback(self, payload: dict[str, Any]) -> dict:
        """Forward feedback to n8n. Short timeout — it's a write-only path."""
        return self._post("feedback", payload, timeout=10)
