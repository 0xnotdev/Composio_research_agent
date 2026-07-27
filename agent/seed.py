"""Load and validate the assignment's immutable 100-app seed roster."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .models import AppSeed


REQUIRED_APP_COUNT = 100
REQUIRED_CATEGORY_COUNT = 10
APPS_PER_CATEGORY = 10


def load_seeds(path: str | Path) -> list[AppSeed]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    seeds = [AppSeed(**item) for item in payload]
    validate_seed_roster(seeds)
    return seeds


def validate_seed_roster(seeds: list[AppSeed]) -> None:
    if len(seeds) != REQUIRED_APP_COUNT:
        raise ValueError(f"Expected {REQUIRED_APP_COUNT} apps, got {len(seeds)}")
    ids = [seed.app_id for seed in seeds]
    if len(set(ids)) != len(ids):
        raise ValueError("Seed app_id values must be unique")
    categories = Counter(seed.category for seed in seeds)
    if len(categories) != REQUIRED_CATEGORY_COUNT:
        raise ValueError(f"Expected {REQUIRED_CATEGORY_COUNT} categories, got {len(categories)}")
    invalid = {category: count for category, count in categories.items() if count != APPS_PER_CATEGORY}
    if invalid:
        raise ValueError(f"Each category must have {APPS_PER_CATEGORY} apps: {invalid}")
