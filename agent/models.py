"""Stable domain models and enum values for the research pipeline.

The module avoids third-party runtime dependencies so fixtures and validation can
run before API credentials or package installation are available.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class AuthMethod(StrEnum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    TOKEN = "token"
    OTHER = "other"
    NONE = "none"
    UNKNOWN = "unknown"


class CredentialPath(StrEnum):
    SELF_SERVE = "self_serve"
    PAID_OR_ADMIN_GATED = "paid_or_admin_gated"
    PARTNER_OR_SALES_GATED = "partner_or_sales_gated"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ApiProtocol(StrEnum):
    REST = "rest"
    GRAPHQL = "graphql"
    REST_AND_GRAPHQL = "rest_and_graphql"
    OTHER = "other"
    NONE_PUBLIC = "none_public"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class ApiBreadth(StrEnum):
    NARROW = "narrow"
    MODERATE = "moderate"
    BROAD = "broad"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class Confidence(StrEnum):
    CORROBORATED_PRIMARY = "corroborated_primary"
    SUPPORTED_PRIMARY = "supported_primary"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


class TechnicalViability(StrEnum):
    READY = "ready"
    WORKAROUND_NEEDED = "workaround_needed"
    NO_PUBLIC_API = "no_public_api"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class CombinedBuildability(StrEnum):
    READY_NOW = "ready_now"
    BUILDABLE_WITH_ACCESS_CONSTRAINT = "buildable_with_access_constraint"
    BUILDABLE_WITH_TECHNICAL_WORKAROUND = "buildable_with_technical_workaround"
    BLOCKED = "blocked"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class AppSeed:
    app_id: str
    name: str
    category: str
    hint: str


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    source_id: str
    url: str
    title: str
    source_type: str
    retrieved_at: str
    text: str


@dataclass(frozen=True, slots=True)
class EvidenceExcerpt:
    excerpt_id: str
    source_id: str
    text: str
    dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FieldValue:
    value: Any
    citations: tuple[str, ...] = ()
    confidence: str = Confidence.INSUFFICIENT_EVIDENCE
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["citations"] = list(self.citations)
        return result


@dataclass(slots=True)
class RunManifest:
    run_id: str
    started_at: str
    seed_path: str
    source_policy_version: str
    model: str | None = None
    request_limit: int = 48
    request_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
