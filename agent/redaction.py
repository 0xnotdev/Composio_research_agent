"""Centralized secret redaction for diagnostics and persisted events."""

from __future__ import annotations

import os


SENSITIVE_ENV_NAMES = ("COMPOSIO_API_KEY", "OPENROUTER_API_KEY")


def redact(value: object, secrets: tuple[str, ...] | None = None) -> str:
    text = str(value)
    active_secrets = secrets if secrets is not None else tuple(
        secret for name in SENSITIVE_ENV_NAMES if (secret := os.getenv(name))
    )
    for secret in active_secrets:
        text = text.replace(secret, "[REDACTED]")
    return text
