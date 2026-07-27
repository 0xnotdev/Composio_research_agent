"""Configuration loading with explicit, non-secret defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSIO_API_BASE = "https://backend.composio.dev/api/v3.1"
DEFAULT_REQUEST_LIMIT = 48


def load_dotenv(path: Path | None = None) -> None:
    """Load a simple local .env file without overwriting existing environment values."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    composio_api_key: str | None
    openrouter_api_key: str | None
    openrouter_model: str | None
    composio_api_base: str
    request_limit: int

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        limit = int(os.getenv("OPENROUTER_REQUEST_LIMIT", str(DEFAULT_REQUEST_LIMIT)))
        if not 1 <= limit <= DEFAULT_REQUEST_LIMIT:
            raise ValueError(f"OPENROUTER_REQUEST_LIMIT must be between 1 and {DEFAULT_REQUEST_LIMIT}")
        return cls(
            composio_api_key=os.getenv("COMPOSIO_API_KEY") or None,
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
            openrouter_model=os.getenv("OPENROUTER_MODEL") or None,
            composio_api_base=os.getenv("COMPOSIO_API_BASE", DEFAULT_COMPOSIO_API_BASE).rstrip("/"),
            request_limit=limit,
        )
