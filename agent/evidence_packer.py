"""Deterministic evidence selection for bounded, citation-ready model inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Iterable

from .models import EvidenceExcerpt, EvidenceSource


DIMENSION_TERMS: dict[str, tuple[str, ...]] = {
    "auth": ("oauth", "authentication", "authorize", "api key", "access token", "basic auth"),
    "credential_path": ("free", "trial", "pricing", "paid", "enterprise", "contact sales", "admin"),
    "api_surface": ("api", "rest", "graphql", "endpoint", "developer"),
    "webhooks": ("webhook", "event subscription", "trigger"),
    "mcp": ("model context protocol", "mcp server", "mcp"),
    "sandbox": ("sandbox", "test mode", "test environment"),
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "section", "article", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    text = unescape(" ".join(parser.parts))
    return re.sub(r"[ \t]+", " ", text).replace(" \n", "\n").strip()


def _paragraphs(value: str) -> list[str]:
    text = html_to_text(value) if "<" in value and ">" in value else value
    blocks = re.split(r"\n{2,}|(?<=[.!?])\s{2,}", text)
    return [re.sub(r"\s+", " ", block).strip() for block in blocks if len(block.strip()) >= 40]


def _score(text: str) -> tuple[int, tuple[str, ...]]:
    lower = text.lower()
    dimensions = tuple(
        dimension for dimension, terms in DIMENSION_TERMS.items() if any(term in lower for term in terms)
    )
    # Prefer field-dense, bounded paragraphs while avoiding boilerplate-sized blobs.
    score = len(dimensions) * 100 + sum(lower.count(term) for terms in DIMENSION_TERMS.values() for term in terms)
    score -= max(0, len(text) - 900) // 25
    return score, dimensions


@dataclass(frozen=True, slots=True)
class EvidencePack:
    excerpts: tuple[EvidenceExcerpt, ...]
    omitted_characters: int

    def as_prompt_payload(self, sources: dict[str, EvidenceSource]) -> list[dict[str, str | list[str]]]:
        return [
            {
                "id": excerpt.excerpt_id,
                "url": sources[excerpt.source_id].url,
                "title": sources[excerpt.source_id].title,
                "text": excerpt.text,
                "dimensions": list(excerpt.dimensions),
            }
            for excerpt in self.excerpts
        ]


def build_evidence_pack(sources: Iterable[EvidenceSource], max_characters: int = 4500) -> EvidencePack:
    if max_characters < 200:
        raise ValueError("max_characters must be at least 200")
    candidates: list[tuple[int, str, str, tuple[str, ...]]] = []
    total_source_characters = 0
    for source in sources:
        total_source_characters += len(source.text)
        for paragraph in _paragraphs(source.text):
            score, dimensions = _score(paragraph)
            if dimensions:
                candidates.append((score, source.source_id, paragraph, dimensions))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    excerpts: list[EvidenceExcerpt] = []
    consumed = 0
    seen: set[tuple[str, str]] = set()
    for _, source_id, paragraph, dimensions in candidates:
        fingerprint = (source_id, paragraph)
        if fingerprint in seen:
            continue
        remaining = max_characters - consumed
        if remaining < 120:
            break
        clipped = paragraph[:remaining].rsplit(" ", 1)[0].strip() if len(paragraph) > remaining else paragraph
        if len(clipped) < 80:
            continue
        seen.add(fingerprint)
        excerpts.append(EvidenceExcerpt(f"E{len(excerpts) + 1:02d}", source_id, clipped, dimensions))
        consumed += len(clipped)

    return EvidencePack(tuple(excerpts), max(0, total_source_characters - consumed))
