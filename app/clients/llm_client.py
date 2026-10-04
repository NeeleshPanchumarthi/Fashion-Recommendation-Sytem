"""Groq chat-completions client (OpenAI-compatible HTTP API).

The only module that knows Groq's endpoint and request format. Callers get
parsed JSON or a DependencyUnavailableError -- never a raw HTTP error.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.exceptions import DependencyUnavailableError

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEPENDENCY = "llm"


class LLMClient:
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 6.0, connect_attempts: int = 2) -> None:
        self._api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.connect_attempts = max(1, connect_attempts)

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Ask the model for a JSON object and return it parsed."""
        if not self.enabled:
            raise DependencyUnavailableError(DEPENDENCY, "No LLM API key is configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            # Reasoning models (gpt-oss) spend tokens thinking before the JSON;
            # too small a budget truncates the JSON and Groq returns a 400.
            "max_tokens": 1024,
        }
        if "gpt-oss" in self.model:
            payload["reasoning_effort"] = "low"

        try:
            resp = self._post(payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except DependencyUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 -- HTTP status, bad JSON, missing keys
            raise DependencyUnavailableError(DEPENDENCY, f"LLM request failed: {exc}") from exc

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        # Connection resets (WinError 10054) during the TLS handshake are
        # common on some networks; a quick retry usually gets through.
        for attempt in range(1, self.connect_attempts + 1):
            try:
                return httpx.post(
                    GROQ_CHAT_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx.ConnectError as exc:
                if attempt == self.connect_attempts:
                    raise DependencyUnavailableError(DEPENDENCY, f"Could not reach the LLM: {exc}") from exc
        raise AssertionError("unreachable")
