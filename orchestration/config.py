from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql+psycopg://krishi:krishi@localhost:5432/krishi_awaaz"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    scenario_file: Path = Path("data/scenarios.json")

    @classmethod
    def from_environment(cls, scenario_file: Path | None = None) -> Settings:
        return cls(
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            scenario_file=scenario_file or Path("data/scenarios.json"),
        )
