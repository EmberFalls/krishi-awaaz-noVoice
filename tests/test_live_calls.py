import asyncio
from collections import deque
from pathlib import Path

from agents.models import DialogueLine, SimulationResult, SpeakerType
from data.scenarios import load_scenarios
from orchestration.workflow import execute_scenario
from telephony.contracts import AudioInput, CallStatus, SynthesizedSpeech, TranscriptionResult
from telephony.live import LiveCallCoordinator

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


class StubSpeechToText:
    def __init__(self, lines: list[DialogueLine]) -> None:
        self._lines = deque(lines)

    async def transcribe(
        self, audio: AudioInput, *, language_hint: str | None = None
    ) -> TranscriptionResult:
        line = self._lines.popleft()
        return TranscriptionResult(text=line.text, language=line.language, confidence=0.92)


class StubTextToSpeech:
    def __init__(self) -> None:
        self.clips: list[SynthesizedSpeech] = []

    async def synthesize(self, text: str, *, language: str) -> SynthesizedSpeech:
        clip = SynthesizedSpeech(
            clip_id=f"clip-{len(self.clips) + 1}",
            text=text,
            language=language,
            audio_reference=f"memory://test/{len(self.clips) + 1}",
            content=b"test-audio",
        )
        self.clips.append(clip)
        return clip


def normalize_result(result: SimulationResult) -> dict[str, object]:
    payload = result.model_dump(mode="json")
    payload["run_id"] = "normalized"
    return payload


def test_live_call_coordinator_collects_free_form_facts_and_preserves_workflow_output() -> None:
    scenario = load_scenarios(CATALOG)[0]
    farmer_lines = [line for line in scenario.intake_dialogue if line.speaker is SpeakerType.FARMER]
    coordinator = LiveCallCoordinator(
        [scenario],
        StubSpeechToText(farmer_lines),
        StubTextToSpeech(),
    )

    session, first_prompt = asyncio.run(
        coordinator.start_call("CA-test", "+910000000000", scenario.id)
    )
    assert first_prompt.text == "तुम्ही कोणते पीक विकत आहात?"

    for index in range(len(farmer_lines)):
        session, _ = asyncio.run(
            coordinator.accept_recording(
                session.call_id,
                AudioInput(audio_reference=f"memory://recording/{index}", content=b"caller-audio"),
            )
        )
        if session.status is CallStatus.COMPLETED:
            break

    assert session.status is CallStatus.COMPLETED
    assert len([line for line in session.dialogue if line.speaker is SpeakerType.FARMER]) == 2
    assert normalize_result(coordinator.get_result(session.call_id)) == normalize_result(
        asyncio.run(execute_scenario(scenario))
    )
