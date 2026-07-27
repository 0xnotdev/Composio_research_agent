"""Secondary Composio toolkit-catalog signal; never a primary research source."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


class ComposioCatalogClient:
    def __init__(self, api_key: str, api_base: str, timeout_seconds: int = 45) -> None:
        self.api_key, self.api_base, self.timeout_seconds = api_key, api_base.rstrip("/"), timeout_seconds

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        suffix = f"?{urlencode(params)}" if params else ""
        request = Request(f"{self.api_base}{path}{suffix}", headers={"x-api-key": self.api_key})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Composio catalog request failed: {error}") from error

    def list_all(self) -> list[dict[str, Any]]:
        cursor: str | None = None
        items: list[dict[str, Any]] = []
        for _ in range(100):
            payload = self._get("/toolkits", {"limit": 100, **({"cursor": cursor} if cursor else {})})
            container = payload.get("data", payload) if isinstance(payload, dict) else {}
            page = container.get("items", container.get("toolkits", [])) if isinstance(container, dict) else []
            items.extend(item for item in page if isinstance(item, dict))
            cursor = container.get("next_cursor") or container.get("nextCursor") if isinstance(container, dict) else None
            if not cursor:
                return items
        raise RuntimeError("Composio catalog pagination exceeded 100 pages")


def cross_check(records: list[dict[str, Any]], toolkits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for toolkit in toolkits:
        for value in (toolkit.get("slug"), toolkit.get("name")):
            if isinstance(value, str):
                index.setdefault(normalise(value), toolkit)
    for record in records:
        match = index.get(normalise(record["app_id"])) or index.get(normalise(record.get("name", "")))
        if match is None:
            record["composio_cross_check"] = {"match_status": "no_confident_match", "notes": "secondary catalog signal only"}
            continue
        record["composio_cross_check"] = {
            "match_status": "matched",
            "toolkit_slug": match.get("slug"),
            "toolkit_name": match.get("name"),
            "tool_count": match.get("tool_count", match.get("toolCount")),
            "notes": "secondary catalog signal only; vendor documentation remains primary evidence",
        }
    return records
