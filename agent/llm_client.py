"""Small OpenRouter client with a hard request ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RequestBudgetExceeded(RuntimeError):
    pass


class LlmTransportError(RuntimeError):
    pass


class ChatClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


@dataclass(slots=True)
class RequestLedger:
    limit: int = 48
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.events)

    def reserve(self, purpose: str) -> None:
        if self.count >= self.limit:
            raise RequestBudgetExceeded(f"OpenRouter request limit ({self.limit}) reached")
        self.events.append({"at": datetime.now(UTC).isoformat(), "purpose": purpose})


@dataclass(slots=True)
class OpenRouterClient:
    api_key: str
    model: str
    ledger: RequestLedger
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"
    timeout_seconds: int = 90

    def complete(self, *, system: str, user: str, purpose: str = "research") -> str:
        self.ledger.reserve(purpose)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
            }
        ).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LlmTransportError(f"OpenRouter request failed: {error}") from error
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise LlmTransportError("OpenRouter response lacked assistant content") from error
