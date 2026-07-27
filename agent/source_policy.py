"""Official-source allowlisting.

Search can discover URLs, but only this policy decides whether a discovered page
is admissible evidence. The policy deliberately defaults to rejection whenever
the ownership relation cannot be established from the assignment hint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .models import AppSeed


def _normalise_url(value: str) -> str:
    return value if "://" in value else f"https://{value}"


def _host(value: str) -> str:
    return (urlparse(_normalise_url(value)).hostname or "").lower().rstrip(".")


def _registrable_suffix(host: str) -> str | None:
    """A conservative two-label suffix for the supplied assignment domains.

    This intentionally does not attempt a general public-suffix implementation.
    Shared hosts are handled separately and unknown TLD structures require an
    explicit policy override instead of a permissive guess.
    """
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else None


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    version: str
    shared_hosts: frozenset[str]
    overrides: dict[str, dict]

    @classmethod
    def load(cls, path: str | Path) -> "SourcePolicy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            version=str(payload["version"]),
            shared_hosts=frozenset(item.lower() for item in payload.get("shared_hosts", [])),
            overrides=dict(payload.get("overrides", {})),
        )

    def is_accepted(self, seed: AppSeed, candidate_url: str) -> bool:
        parsed = urlparse(_normalise_url(candidate_url))
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        host = parsed.hostname.lower().rstrip(".")
        path = parsed.path.rstrip("/") or "/"
        override = self.overrides.get(seed.app_id, {})
        allowed_hosts = {item.lower() for item in override.get("allowed_hosts", [])}
        allowed_prefixes = tuple(item.rstrip("/") for item in override.get("allowed_path_prefixes", []))

        if allowed_hosts:
            if host not in allowed_hosts:
                return False
            return not allowed_prefixes or any(path == prefix or path.startswith(f"{prefix}/") for prefix in allowed_prefixes)

        hint_host = _host(seed.hint)
        if not hint_host:
            return False
        if hint_host in self.shared_hosts:
            return host == hint_host
        suffix = _registrable_suffix(hint_host)
        if suffix is None:
            return host == hint_host
        return host == suffix or host.endswith(f".{suffix}")

    def explain_rejection(self, seed: AppSeed, candidate_url: str) -> str:
        if self.is_accepted(seed, candidate_url):
            return "accepted"
        return f"Rejected non-authoritative source for {seed.app_id}: {candidate_url}"
