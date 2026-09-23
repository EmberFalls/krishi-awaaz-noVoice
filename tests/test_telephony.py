import asyncio
from pathlib import Path

from agents.models import SimulationResult
from data.scenarios import load_scenarios
from orchestration.workflow import execute_scenario
from telephony.contracts import CallStatus
from telephony.service import run_scripted_voice_call

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


def normalize_result(result: SimulationResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["run_id"] = "normalized"
    return payload


def test_scripted_voice_calls_replay_intake_and_preserve_workflow_output() -> None:
    for scenario in load_scenarios(CATALOG):
        voice_call = asyncio.run(run_scripted_voice_call(scenario))
        text_result = asyncio.run(execute_scenario(scenario))

        assert voice_call.session.status is CallStatus.COMPLETED
        assert [line.text for line in voice_call.session.dialogue] == [
            line.text for line in scenario.intake_dialogue
        ]
        assert [line.language for line in voice_call.session.dialogue] == [
            line.language for line in scenario.intake_dialogue
        ]
        assert len(voice_call.synthesized_prompts) == sum(
            line.speaker.value != "farmer" for line in scenario.intake_dialogue
        )
        assert normalize_result(voice_call.workflow_result) == normalize_result(text_result)
