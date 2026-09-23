from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from agents.models import SimulationScenario

SCENARIO_LIST = TypeAdapter(list[SimulationScenario])


def load_scenarios(path: Path) -> list[SimulationScenario]:
    if not path.exists():
        raise FileNotFoundError(f"Scenario catalog not found: {path.resolve()}")
    with path.open("r", encoding="utf-8") as handle:
        return SCENARIO_LIST.validate_python(json.load(handle))


def find_scenario(scenarios: list[SimulationScenario], scenario_id: str) -> SimulationScenario:
    for scenario in scenarios:
        if scenario.id == scenario_id:
            return scenario
    available = ", ".join(scenario.id for scenario in scenarios)
    raise KeyError(f"Unknown scenario '{scenario_id}'. Available scenarios: {available}")
