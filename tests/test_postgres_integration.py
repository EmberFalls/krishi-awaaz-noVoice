"""Opt-in real PostgreSQL persistence test used by scripts/run_tests.ps1."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from data.scenarios import load_scenarios
from db.database import PostgresStore, SimulationRunRow
from orchestration.workflow import execute_scenario

pytestmark = pytest.mark.integration
CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="Set RUN_POSTGRES_TESTS=1 after starting the local PostgreSQL container.",
)
def test_postgres_saves_a_full_simulation_run() -> None:
    store = PostgresStore(
        os.getenv("DATABASE_URL", "postgresql+psycopg://krishi:krishi@localhost:5432/krishi_awaaz")
    )
    scenario = load_scenarios(CATALOG)[0]
    result = asyncio.run(execute_scenario(scenario))
    try:
        store.create_schema()
        store.save_result(scenario, result)
        with Session(store.engine) as session:
            saved = session.scalar(
                select(SimulationRunRow).where(SimulationRunRow.id == result.run_id)
            )
        assert saved is not None
        assert saved.scenario_id == scenario.id
    finally:
        store.close()
