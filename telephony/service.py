"""Voice-call orchestration that hands completed intake to the existing workflow."""

from __future__ import annotations

from uuid import uuid4

from agents.models import DialogueLine, SimulationScenario, SpeakerType
from orchestration.workflow import execute_scenario

from .contracts import AudioInput, CallSession, CallStatus, VoiceCallResult
from .simulated import CapturingTextToSpeech, ScriptedSpeechToText


async def run_scripted_voice_call(scenario: SimulationScenario) -> VoiceCallResult:
    """Replay a scenario as a local voice call, then run the unchanged workflow.

    Farmer turns pass through the simulated speech recognizer and intake-agent
    turns pass through the simulated text-to-speech provider. The existing
    deterministic workflow receives the same scenario as the text demo, so its
    negotiation and ranking output remains unchanged.
    """

    session = CallSession(
        call_id=str(uuid4()),
        scenario_id=scenario.id,
        caller_reference=f"demo:{scenario.farmer.phone_alias}",
        preferred_language=scenario.farmer.preferred_language,
    )
    recognizer = ScriptedSpeechToText(
        line for line in scenario.intake_dialogue if line.speaker is SpeakerType.FARMER
    )
    synthesizer = CapturingTextToSpeech()
    session.status = CallStatus.CONNECTED
    session.events.append("Connected a local simulated call.")

    try:
        for turn_number, line in enumerate(scenario.intake_dialogue, start=1):
            if line.speaker is SpeakerType.FARMER:
                transcription = await recognizer.transcribe(
                    AudioInput(
                        audio_reference=f"simulated://caller/{turn_number}",
                        content=b"simulated-audio",
                    ),
                    language_hint=scenario.farmer.preferred_language,
                )
                session.dialogue.append(
                    DialogueLine(
                        speaker=SpeakerType.FARMER,
                        text=transcription.text,
                        english_translation=line.english_translation,
                        language=transcription.language,
                        speaker_id=line.speaker_id,
                        metadata={
                            **line.metadata,
                            "transcription_confidence": transcription.confidence,
                        },
                    )
                )
                continue

            await synthesizer.synthesize(line.text, language=line.language)
            session.dialogue.append(line)

        session.status = CallStatus.INTAKE_COMPLETE
        session.events.append("Completed scripted speech intake.")
        workflow_result = await execute_scenario(scenario)
        session.status = CallStatus.COMPLETED
        session.events.append("Completed the existing negotiation workflow.")
    except Exception:
        session.status = CallStatus.FAILED
        session.events.append("The simulated call failed.")
        raise

    return VoiceCallResult(
        session=session,
        synthesized_prompts=synthesizer.clips,
        workflow_result=workflow_result,
    )
