"""Official documentation retrieval with Composio-first and HTTP fallback paths."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import AppSeed, EvidenceSource
from .source_policy import SourcePolicy


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FetchResponse:
    requested_url: str
    final_url: str
    title: str
    text: str
    content_type: str
    transport: str


@dataclass(frozen=True, slots=True)
class EvidenceAcquisition:
    source: EvidenceSource | None
    transport: str
    failure: str | None = None


class UrlFetcher(Protocol):
    def fetch(self, url: str) -> FetchResponse: ...


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title.append(data)


def _title_from_html(value: str) -> str:
    parser = _TitleParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", unescape(" ".join(parser.title))).strip() or "Untitled official source"


def _normalise_url(value: str) -> str:
    return value if value.startswith(("https://", "http://")) else f"https://{value}"


class HttpFetcher:
    """Read-only fallback for public documentation; enforces response-size limits."""

    def __init__(self, timeout_seconds: int = 25, max_bytes: int = 2_000_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def fetch(self, url: str) -> FetchResponse:
        normalised = _normalise_url(url)
        parsed = urlparse(normalised)
        if parsed.scheme != "https":
            raise FetchError("Only HTTPS source URLs are allowed")
        request = Request(normalised, headers={"User-Agent": "ComposioResearchAgent/0.1 (+research assignment)"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise FetchError(f"Response exceeds {self.max_bytes} byte safety limit")
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                final_url = response.geturl()
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            raise FetchError(f"HTTP retrieval failed for {normalised}: {error}") from error
        title = _title_from_html(text) if "html" in content_type else "Official documentation"
        return FetchResponse(normalised, final_url, title, text, content_type, "http_fallback")


class ComposioSearchFetcher:
    """Minimal REST adapter. Tool schemas are verified before any live run.

    The default argument shape is intentionally isolated here because the current
    Composio tool schema must be inspected at Checkpoint 0 before the live batch.
    """

    TOOL_SLUG = "COMPOSIO_SEARCH_FETCH_URL_CONTENT"

    def __init__(self, api_key: str, api_base: str, timeout_seconds: int = 45) -> None:
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.api_base}{path}",
            data=encoded,
            method=method,
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise FetchError(f"Composio API request failed: {error}") from error

    def inspect_tool_schema(self) -> Any:
        return self._request("GET", f"/tools/{self.TOOL_SLUG}")

    def fetch(self, url: str) -> FetchResponse:
        # Checkpoint 0 must compare this request body to inspect_tool_schema().
        payload = self._request(
            "POST",
            f"/tools/execute/{self.TOOL_SLUG}",
            {"arguments": {"url": _normalise_url(url)}, "version": "latest"},
        )
        result = payload.get("data", payload)
        if not isinstance(result, dict):
            raise FetchError("Composio fetch returned an unexpected non-object payload")
        content = result.get("content") or result.get("text") or result.get("data")
        if not isinstance(content, str) or not content.strip():
            raise FetchError("Composio fetch returned no readable content")
        final_url = str(result.get("url") or url)
        return FetchResponse(_normalise_url(url), final_url, str(result.get("title") or "Official documentation"), content, "text/plain", "composio_search")


class ResilientFetcher:
    def __init__(self, primary: UrlFetcher | None, fallback: UrlFetcher | None) -> None:
        self.primary = primary
        self.fallback = fallback

    def fetch(self, url: str) -> FetchResponse:
        primary_error: FetchError | None = None
        if self.primary is not None:
            try:
                return self.primary.fetch(url)
            except FetchError as error:
                primary_error = error
        if self.fallback is not None:
            try:
                return self.fallback.fetch(url)
            except FetchError as fallback_error:
                message = f"primary={primary_error}; fallback={fallback_error}" if primary_error else str(fallback_error)
                raise FetchError(message) from fallback_error
        raise primary_error or FetchError("No fetch transport configured")


def acquire_hint_evidence(seed: AppSeed, fetcher: UrlFetcher, policy: SourcePolicy) -> EvidenceAcquisition:
    try:
        response = fetcher.fetch(seed.hint)
    except FetchError as error:
        return EvidenceAcquisition(None, "failed", str(error))
    if not policy.is_accepted(seed, response.final_url):
        return EvidenceAcquisition(None, response.transport, policy.explain_rejection(seed, response.final_url))
    source = EvidenceSource(
        source_id="S01",
        url=response.final_url,
        title=response.title,
        source_type="official_docs",
        retrieved_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        text=response.text,
    )
    return EvidenceAcquisition(source, response.transport)


def acquisition_to_dict(acquisition: EvidenceAcquisition) -> dict[str, Any]:
    return {"source": asdict(acquisition.source) if acquisition.source else None, "transport": acquisition.transport, "failure": acquisition.failure}
